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

import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

app = FastAPI(title="Logistics Agent API", version="1.0.0")



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


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "logistics-agent-api"}


# ---------------------------------------------------------------------------
# 1) Full pipeline — recommended entry points (mirrors backend_service.py)
# ---------------------------------------------------------------------------

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
