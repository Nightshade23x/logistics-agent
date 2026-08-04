# API SERVER
# Defines the HTTP endpoints used by the frontend.
# The text endpoint passes shipment requests to the backend service.

"""
Thin HTTP API layer over the existing Python agent pipeline.

This file does NOT change any agent logic. It only exposes:

  1. The three stable "backend_service" entry points (recommended for a real
     frontend to use — they run the full pipeline and return the enriched
     frontend payload documented in ARCHITECTURE.md §5.4).

  2. Direct, single-agent endpoints (for the "Partner Agents" / debugging
     playground page in the frontend) that call one specialist module in
     isolation, e.g. just the Logistics Agent or just the Shopping Agent,
     without running the whole pipeline.

Run with:
    pip install fastapi uvicorn python-multipart
    uvicorn api_server:app --reload --port 8000
"""

from __future__ import annotations
import json as _json
from starlette.requests import Request as _StarletteRequest
from starlette.responses import Response as _StarletteResponse
from app.frontend_response_cleanup import cleanup_frontend_response

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.backend_service import (
    process_document_files_request,
    process_json_file_request,
    process_text_request,
)
from app.logistics_agent import build_logistics_plan
from app.shopping_agent import build_shopping_plan
from app.document_service import run_document_agent_from_text
from app.partner_review_service import run_partner_review
from app.agent_router import detect_text_intent
from app.integrations.service import (
    check_integrations,
    get_carrier_quotes,
    get_integration_contract,
    list_integrations,
)

app = FastAPI(
    title="Logistics Agent API",
    version="1.1.0",
    description="Shipping-planning API with provider-neutral company and carrier integrations.",
)



# Final API cleanup middleware.
# This runs after the user-agent/compact-payload/report builders so React receives cleaned JSON.
if not getattr(app.state, "frontend_response_cleanup_middleware_installed", False):
    app.state.frontend_response_cleanup_middleware_installed = True

    @app.middleware("http")
    async def _frontend_response_cleanup_middleware(request: _StarletteRequest, call_next):
        body_bytes = b""
        original_text = None

        if request.url.path.startswith("/api/request/"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_json = _json.loads(body_bytes.decode("utf-8"))
                    if isinstance(body_json, dict):
                        original_text = (
                            body_json.get("user_text")
                            or body_json.get("text")
                            or body_json.get("prompt")
                            or body_json.get("request_text")
                        )
            except Exception:
                body_bytes = body_bytes or b""

            async def _receive():
                return {
                    "type": "http.request",
                    "body": body_bytes,
                    "more_body": False,
                }

            request = _StarletteRequest(request.scope, _receive)

        response = await call_next(request)

        if not request.url.path.startswith("/api/request/"):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response

        try:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            payload = _json.loads(response_body.decode("utf-8"))
            cleaned = cleanup_frontend_response(payload, original_text)

            cleaned_body = _json.dumps(cleaned, default=str).encode("utf-8")

            headers = dict(response.headers)
            headers.pop("content-length", None)

            return _StarletteResponse(
                content=cleaned_body,
                status_code=response.status_code,
                headers=headers,
                media_type="application/json",
            )

        except Exception:
            return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TextRequest(BaseModel):
    user_text: str
    include_raw_response: bool = False


class JsonRequest(BaseModel):
    payload: dict[str, Any]
    include_raw_response: bool = False


class LogisticsRequest(BaseModel):
    items: list[dict[str, Any]]
    shipment_context: Optional[dict[str, Any]] = None


class ShoppingRequest(BaseModel):
    request_data: dict[str, Any]


class DocumentTextRequest(BaseModel):
    text: str


class PartnerReviewRequest(BaseModel):
    payload: dict[str, Any]
    request_id: Optional[str] = None


class IntentRequest(BaseModel):
    text: str


class CarrierQuoteRequest(BaseModel):
    origin_country: str
    destination_country: str
    total_weight_kg: Optional[float] = None
    total_cbm: Optional[float] = None
    package_count: int = 1
    declared_value_usd: Optional[float] = None
    currency: str = "USD"
    hazardous: bool = False
    pickup_postal_code: Optional[str] = None
    delivery_postal_code: Optional[str] = None
    provider_ids: Optional[list[str]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "logistics-agent-api"}


# ---------------------------------------------------------------------------
# 1) Full pipeline — recommended entry points (mirrors backend_service.py)
# ---------------------------------------------------------------------------

# MAIN TEXT REQUEST ENDPOINT
# Receives the shipment request from POST /api/request/text.
# It calls backend_service.process_text_request and returns JSON.

@app.post("/api/request/text")
def request_text(body: TextRequest) -> dict[str, Any]:
    return process_text_request(body.user_text, include_raw_response=body.include_raw_response)


@app.post("/api/request/json")
def request_json(body: JsonRequest) -> dict[str, Any]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="req-json-"))
    tmp_path = tmp_dir / "request.json"
    import json

    tmp_path.write_text(json.dumps(body.payload), encoding="utf-8")
    try:
        return process_json_file_request(tmp_path, include_raw_response=body.include_raw_response)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/request/documents")
async def request_documents(
    files: list[UploadFile] = File(...),
    include_raw_response: bool = False,
) -> dict[str, Any]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="req-docs-"))
    saved_paths: list[Path] = []
    try:
        for upload in files:
            dest = tmp_dir / upload.filename
            with dest.open("wb") as f:
                shutil.copyfileobj(upload.file, f)
            saved_paths.append(dest)

        return process_document_files_request(saved_paths, include_raw_response=include_raw_response)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 2) Individual specialist-agent endpoints (debugging / partner-agent playground)
# ---------------------------------------------------------------------------

@app.post("/api/agents/logistics")
def agent_logistics(body: LogisticsRequest) -> dict[str, Any]:
    try:
        return build_logistics_plan(body.items, body.shipment_context)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/agents/shopping")
def agent_shopping(body: ShoppingRequest) -> dict[str, Any]:
    try:
        return build_shopping_plan(body.request_data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/agents/document")
def agent_document(body: DocumentTextRequest) -> dict[str, Any]:
    try:
        return run_document_agent_from_text(body.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/agents/partner-review")
def agent_partner_review(body: PartnerReviewRequest) -> dict[str, Any]:
    try:
        return run_partner_review(body.payload, request_id=body.request_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/agents/intent")
def agent_intent(body: IntentRequest) -> dict[str, Any]:
    try:
        return detect_text_intent(body.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# 3) Provider-neutral company/carrier integrations
# INTEGRATION_UX_FOUNDATION_V37
# ---------------------------------------------------------------------------

def _require_optional_integration_key(x_api_key: Optional[str]) -> None:
    expected = str(os.getenv("LOGISTICS_INTEGRATION_API_KEY") or "").strip()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="A valid X-API-Key is required for integration endpoints.")


def _model_payload(body: BaseModel) -> dict[str, Any]:
    if hasattr(body, "model_dump"):
        return body.model_dump()
    return body.dict()


@app.get("/api/integrations", tags=["Integrations"])
def integrations_list(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> dict[str, Any]:
    _require_optional_integration_key(x_api_key)
    return list_integrations()


@app.get("/api/integrations/health", tags=["Integrations"])
def integrations_health(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> dict[str, Any]:
    _require_optional_integration_key(x_api_key)
    return check_integrations()


@app.get("/api/integrations/contract", tags=["Integrations"])
def integrations_contract(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> dict[str, Any]:
    _require_optional_integration_key(x_api_key)
    return get_integration_contract()


@app.post("/api/integrations/quotes", tags=["Integrations"])
def integrations_quotes(
    body: CarrierQuoteRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _require_optional_integration_key(x_api_key)
    try:
        return get_carrier_quotes(_model_payload(body))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# FASTAPI FINAL WEIGHT AUTHORITY V85
# The API route may retain an earlier backend/interpreter callable. Wrap the
# completed route endpoint so the original request text is used to canonicalise
# the final JSON payload immediately before FastAPI serialises it.
def _v85_collect_request_text(value, candidates, seen):
    object_id = id(value)
    if object_id in seen:
        return
    seen.add(object_id)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return

        lowered = stripped.lower()
        score = min(len(stripped), 500)

        if "ship" in lowered:
            score += 2000
        if " from " in lowered and " to " in lowered:
            score += 1000
        if any(
            token in lowered
            for token in (
                " lb",
                " lbs",
                " pound",
                " kg",
                " cbm",
                "crate",
                "pallet",
            )
        ):
            score += 700

        candidates.append((score, stripped))
        return

    if isinstance(value, dict):
        priority_keys = (
            "user_text",
            "request_text",
            "user_request",
            "prompt",
            "text",
            "original_text",
            "input_text",
        )

        for key in priority_keys:
            if key in value:
                _v85_collect_request_text(
                    value.get(key),
                    candidates,
                    seen,
                )

        for key, child in value.items():
            if key not in priority_keys:
                _v85_collect_request_text(
                    child,
                    candidates,
                    seen,
                )
        return

    if isinstance(value, (list, tuple)):
        for child in value:
            _v85_collect_request_text(
                child,
                candidates,
                seen,
            )
        return

    for attribute in (
        "user_text",
        "request_text",
        "user_request",
        "prompt",
        "text",
        "original_text",
        "input_text",
    ):
        try:
            child = getattr(value, attribute)
        except Exception:
            continue

        _v85_collect_request_text(
            child,
            candidates,
            seen,
        )

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
        except Exception:
            dumped = None

        if dumped is not None:
            _v85_collect_request_text(
                dumped,
                candidates,
                seen,
            )


def _v85_original_request_text(args, kwargs):
    candidates = []
    seen = set()

    _v85_collect_request_text(
        args,
        candidates,
        seen,
    )
    _v85_collect_request_text(
        kwargs,
        candidates,
        seen,
    )

    if not candidates:
        return ""

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )
    return candidates[0][1]


def _v85_finalize_payload(payload, original_text):
    if not isinstance(payload, dict):
        return payload

    from app.practical_imperial_precision_v80 import (
        apply_practical_imperial_precision,
    )
    from app.backend_service import (
        _v83_apply_final_weight_text_contract,
    )

    payload = apply_practical_imperial_precision(
        payload,
        original_text,
    )
    payload = _v83_apply_final_weight_text_contract(
        payload,
    )

    metadata = payload.setdefault(
        "request_metadata",
        {},
    )
    if isinstance(metadata, dict):
        metadata["fastapi_final_weight_authority_v85"] = {
            "status": "applied",
            "request_text_found": bool(original_text),
        }

    return payload


def _v85_finalize_route_result(result, original_text):
    if isinstance(result, dict):
        return _v85_finalize_payload(
            result,
            original_text,
        )

    model_dump = getattr(result, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
        except Exception:
            dumped = None

        if isinstance(dumped, dict):
            return _v85_finalize_payload(
                dumped,
                original_text,
            )

    body = getattr(result, "body", None)
    if isinstance(body, (bytes, bytearray)):
        import json as _v85_json

        try:
            decoded = _v85_json.loads(
                bytes(body).decode("utf-8")
            )
        except Exception:
            decoded = None

        if isinstance(decoded, dict):
            from fastapi.responses import JSONResponse

            decoded = _v85_finalize_payload(
                decoded,
                original_text,
            )

            headers = {
                key: value
                for key, value in result.headers.items()
                if key.lower()
                not in {
                    "content-length",
                    "content-type",
                }
            }

            return JSONResponse(
                content=decoded,
                status_code=getattr(
                    result,
                    "status_code",
                    200,
                ),
                headers=headers,
                background=getattr(
                    result,
                    "background",
                    None,
                ),
            )

    return result


def _v85_install_request_text_route_wrapper():
    import inspect as _v85_inspect

    for route in getattr(app, "routes", []):
        if getattr(route, "path", None) != "/api/request/text":
            continue

        methods = getattr(route, "methods", set()) or set()
        if "POST" not in methods:
            continue

        original = getattr(route, "endpoint", None)
        if original is None:
            continue

        if getattr(
            original,
            "_fastapi_final_weight_authority_v85",
            False,
        ):
            continue

        if _v85_inspect.iscoroutinefunction(original):
            async def wrapped(
                *args,
                __original=original,
                **kwargs,
            ):
                original_text = _v85_original_request_text(
                    args,
                    kwargs,
                )
                result = await __original(
                    *args,
                    **kwargs,
                )
                return _v85_finalize_route_result(
                    result,
                    original_text,
                )
        else:
            def wrapped(
                *args,
                __original=original,
                **kwargs,
            ):
                original_text = _v85_original_request_text(
                    args,
                    kwargs,
                )
                result = __original(
                    *args,
                    **kwargs,
                )
                return _v85_finalize_route_result(
                    result,
                    original_text,
                )

        wrapped.__name__ = getattr(
            original,
            "__name__",
            "request_text_v85",
        )
        wrapped.__doc__ = getattr(
            original,
            "__doc__",
            None,
        )
        wrapped.__signature__ = _v85_inspect.signature(
            original
        )
        wrapped._fastapi_final_weight_authority_v85 = True

        route.endpoint = wrapped

        dependant = getattr(route, "dependant", None)
        if dependant is not None:
            dependant.call = wrapped



_v85_install_request_text_route_wrapper()


# FASTAPI RESPONSE FINAL WEIGHT AUTHORITY V87
# Final response-only correction for POST /api/request/text.
# This middleware avoids replacing FastAPI's cached APIRoute application.
@app.middleware("http")
async def _fastapi_final_weight_authority_v87_middleware(
    request,
    call_next,
):
    import json as _v87_json

    is_target = (
        request.method.upper() == "POST"
        and request.url.path == "/api/request/text"
    )
    original_text = ""

    if is_target:
        try:
            request_body = await request.body()
            request_data = _v87_json.loads(
                request_body.decode("utf-8")
            )
            if isinstance(request_data, dict):
                original_text = str(
                    request_data.get("user_text")
                    or request_data.get("request_text")
                    or request_data.get("text")
                    or ""
                )
        except Exception:
            original_text = ""

    response = await call_next(request)

    if (
        not is_target
        or response.status_code != 200
        or "application/json"
        not in response.headers.get(
            "content-type",
            "",
        ).lower()
    ):
        return response

    raw_body = b""

    try:
        chunks = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
            elif isinstance(chunk, bytearray):
                chunks.append(bytes(chunk))
            elif isinstance(chunk, memoryview):
                chunks.append(chunk.tobytes())
            else:
                chunks.append(str(chunk).encode("utf-8"))

        raw_body = b"".join(chunks)
        payload = _v87_json.loads(
            raw_body.decode("utf-8")
        )

        if not isinstance(payload, dict):
            return response

        from app.practical_imperial_precision_v80 import (
            apply_practical_imperial_precision,
        )
        from app.backend_service import (
            _v83_apply_final_weight_text_contract,
        )

        payload = apply_practical_imperial_precision(
            payload,
            original_text,
        )
        payload = _v83_apply_final_weight_text_contract(
            payload,
        )

        metadata = payload.setdefault(
            "request_metadata",
            {},
        )
        if isinstance(metadata, dict):
            metadata[
                "fastapi_response_final_weight_authority_v87"
            ] = {
                "status": "applied",
                "request_text_found": bool(original_text),
            }

        from fastapi.responses import JSONResponse

        headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower()
            not in {
                "content-length",
                "content-type",
            }
        }

        return JSONResponse(
            content=payload,
            status_code=response.status_code,
            headers=headers,
            background=getattr(
                response,
                "background",
                None,
            ),
        )

    except Exception:
        from starlette.responses import Response

        headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() != "content-length"
        }

        return Response(
            content=raw_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.headers.get(
                "content-type",
                "application/json",
            ).split(";", 1)[0],
            background=getattr(
                response,
                "background",
                None,
            ),
        )
