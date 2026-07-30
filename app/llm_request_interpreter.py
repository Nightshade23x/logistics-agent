from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Any, Callable

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


DEFAULT_MODE = "fallback"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MIN_CONFIDENCE = 0.65
CIRCUIT_BREAK_SECONDS = 30.0

_CIRCUIT_OPEN_UNTIL = 0.0


class CargoFact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    quantity: float | None = None
    package_type: str | None = None
    unit_weight_kg: float | None = None
    total_weight_kg: float | None = None
    total_cbm: float | None = None
    dimensions: str | None = None
    fragile: bool | None = None
    stackable: bool | None = None
    hazardous: bool | None = None


class ShipmentFacts(BaseModel):
    model_config = ConfigDict(extra="ignore")

    origin: str | None = None
    destination: str | None = None
    incoterm: str | None = None
    budget: str | None = None
    transport_mode: str | None = None
    items: list[CargoFact] = Field(default_factory=list)


class LLMInterpretationPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    normalized_text: str
    intent: str = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    corrections: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    shipment: ShipmentFacts = Field(default_factory=ShipmentFacts)


@dataclass(frozen=True)
class InterpretationResult:
    original_text: str
    effective_text: str
    attempted_llm: bool = False
    used_llm: bool = False
    provider: str = "deterministic"
    model: str | None = None
    confidence: float = 0.0
    reason: str = "deterministic_normalization"
    corrections: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    structured_shipment: dict[str, Any] | None = None

    def metadata(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("original_text", None)
        # Keep the accepted rewrite visible for observability and debugging.
        data["effective_text"] = self.effective_text
        return data


TYPO_REPLACEMENTS = {
    # PROMPT_ROBUSTNESS_CORE_V41
    # High-frequency human errors seen in live shipment requests. Replacements
    # are whole-word only and never change explicit numbers or units.
    "calc": "calculate",
    "crat": "crate",
    "crats": "crates",
    "tils": "tiles",
    "frm": "from",
    "wt": "weight",
    "palet": "pallet",
    "palets": "pallets",
    "fragle": "fragile",
    "dont": "do not",
    "landd": "landed",
    "val": "value",
    "insurence": "insurance",
    "broker": "brokerage",
    "batery": "battery",
    "wht": "what",
    "docs": "documents",
    "shp": "ship",
    "shiip": "ship",
    "shipp": "ship",
    "shiping": "shipping",
    "sendng": "sending",
    "frieght": "freight",
    "freigth": "freight",
    "fraglie": "fragile",
    "frgile": "fragile",
    "stackble": "stackable",
    "stackabel": "stackable",
    "nonstackable": "non-stackable",
    "weigth": "weight",
    "wieght": "weight",
    "dimentions": "dimensions",
    "dimensons": "dimensions",
    "destnation": "destination",
    "destinationn": "destination",
    "orgin": "origin",
    "contianer": "container",
    "containr": "container",
    "pallets": "pallets",
    "incotermm": "incoterm",
    "lcll": "LCL",
    "fcll": "FCL",
}

DOMAIN_WORDS = {
    "ship", "shipping", "send", "export", "import", "freight", "container",
    "cargo", "pallet", "pallets", "crate", "crates", "box", "boxes", "cbm",
    "weight", "dimensions", "fragile", "stackable", "hazardous", "origin",
    "destination", "incoterm", "supplier", "suppliers", "documents", "invoice",
    "landed", "cost", "quote", "insurance", "duty", "customs", "delivery",
}

ROUTE_MISSING_MARKERS = {
    "origin", "origin_country", "destination", "destination_country",
    "country_from", "country_to", "pickup_country", "delivery_country",
}


def _mode() -> str:
    value = os.environ.get("LLM_INTERPRETER_MODE", DEFAULT_MODE).strip().lower()
    return value if value in {"off", "fallback", "always"} else DEFAULT_MODE


def _timeout_seconds() -> float:
    try:
        return max(1.0, min(30.0, float(os.environ.get("LLM_INTERPRETER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


def _min_confidence() -> float:
    try:
        return max(0.0, min(1.0, float(os.environ.get("LLM_INTERPRETER_MIN_CONFIDENCE", DEFAULT_MIN_CONFIDENCE))))
    except (TypeError, ValueError):
        return DEFAULT_MIN_CONFIDENCE


_V41_NUMBER = r"(?:\d+(?:\.\d+)?|\.\d+)"
_V41_LENGTH_UNIT = r"(?:millimetres?|millimeters?|mm|centimetres?|centimeters?|cm|metres?|meters?|m|inches?|inch|in|feet|foot|ft)"


def _normalize_dimension_triplets_v41(text: str) -> str:
    """Add parser-friendly separators without changing any value or unit."""
    value = str(text or "")

    explicit_by = re.compile(
        rf"(?P<a>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})\s+by\s+"
        rf"(?P<b>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})\s+by\s+"
        rf"(?P<c>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})",
        flags=re.IGNORECASE,
    )
    value = explicit_by.sub(r"\g<a> x \g<b> x \g<c>", value)

    loose_triplet = re.compile(
        rf"(?P<prefix>\bdimensions?\s*:?[ ]*)"
        rf"(?P<a>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})\s+"
        rf"(?P<b>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})\s+"
        rf"(?P<c>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})",
        flags=re.IGNORECASE,
    )
    value = loose_triplet.sub(r"\g<prefix>\g<a> x \g<b> x \g<c>", value)

    # Common no-punctuation cargo phrasing: "each pallet 1.2 m 1.0 m 1.5 m".
    each_triplet = re.compile(
        rf"(?P<prefix>\beach\s+(?:crate|crates|pallet|pallets|box|boxes|pack|packs|unit|units)\s+)"
        rf"(?P<a>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})\s+"
        rf"(?P<b>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})\s+"
        rf"(?P<c>{_V41_NUMBER}\s*{_V41_LENGTH_UNIT})",
        flags=re.IGNORECASE,
    )
    value = each_triplet.sub(r"\g<prefix>\g<a> x \g<b> x \g<c>", value)
    return value


def normalize_human_text(value: str | None) -> tuple[str, list[str]]:
    original = str(value or "")
    text = unicodedata.normalize("NFKC", original)
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[\r\n]+", ". ", text)
    text = re.sub(r"\s*([,;:!?])\s*", r"\1 ", text)
    text = re.sub(r"([,;:!?]){2,}", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;")

    corrections: list[str] = []
    for wrong, right in TYPO_REPLACEMENTS.items():
        pattern = rf"\b{re.escape(wrong)}\b"
        updated, count = re.subn(pattern, right, text, flags=re.IGNORECASE)
        if count:
            corrections.append(f"{wrong} → {right}")
            text = updated

    text = re.sub(r"\b(kgs)\b", "kg", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(cbm)\s*\.", r"\1", text, flags=re.IGNORECASE)
    text = _normalize_dimension_triplets_v41(text)
    return text.strip(), corrections


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z-]{1,}", text.lower())


def _contains_probable_domain_typo(text: str) -> bool:
    for token in _tokens(text):
        if token in DOMAIN_WORDS or token in TYPO_REPLACEMENTS:
            continue
        if len(token) < 4:
            continue
        for known in DOMAIN_WORDS:
            if abs(len(token) - len(known)) > 2:
                continue
            if SequenceMatcher(None, token, known).ratio() >= 0.84:
                return True
    return False


def _missing_items(response: Any) -> list[str]:
    if not isinstance(response, dict):
        return []
    values: list[str] = []
    for key in ("missing_information", "missing_information_preview"):
        raw = response.get(key)
        if isinstance(raw, list):
            values.extend(str(item).strip().lower() for item in raw if str(item).strip())
    return values


def _response_quality(response: Any) -> float:
    if not isinstance(response, dict):
        return -100.0
    score = 0.0
    intent = str(response.get("detected_intent") or "").strip().lower()
    if intent and intent != "unknown":
        score += 30.0
    agents = response.get("agents_called")
    if isinstance(agents, list) and agents:
        score += min(20.0, len(agents) * 5.0)
    status = str(response.get("status") or response.get("decision") or "").lower()
    if status and not any(word in status for word in ("error", "failed", "unknown")):
        score += 10.0
    if response.get("logistics_visualizer") or response.get("logistics_metrics"):
        score += 10.0
    score -= min(25.0, len(_missing_items(response)) * 1.5)
    return score


def _looks_like_physical_shipment_v41(text: str) -> bool:
    normalized, _ = normalize_human_text(text)
    lower = normalized.lower()
    measurement_hits = re.findall(
        rf"{_V41_NUMBER}\s*{_V41_LENGTH_UNIT}\b",
        lower,
        flags=re.IGNORECASE,
    )
    has_dimensions = len(measurement_hits) >= 3 and (
        " x " in lower or "dimension" in lower or " each " in f" {lower} "
    )
    has_weight = bool(re.search(rf"{_V41_NUMBER}\s*(?:kg|kilograms?|lb|lbs|pounds?)\b", lower))
    has_package = bool(re.search(r"\b(?:crate|crates|pallet|pallets|box|boxes|pack|packs|unit|units)\b", lower))
    has_shipping_context = bool(re.search(r"\b(?:ship|send|freight|cargo|container|export|import)\b", lower))
    has_named_route = (
        bool(re.search(r"\bfrom\s+[a-z][a-z .'-]{1,40}\s+to\s+[a-z]", lower))
        or (" origin " in f" {lower} " and " destination " in f" {lower} ")
        or bool(re.search(r"\b(?:india|china|canada|usa|germany|france|uk|uae)\s+to\s+(?:india|china|canada|usa|germany|france|uk|uae)\b", lower))
    )
    return has_dimensions and has_weight and has_package and (has_shipping_context or has_named_route)


def _nested_positive_number_v41(response: Any, keys: set[str]) -> bool:
    if isinstance(response, dict):
        for key, value in response.items():
            if str(key).lower() in keys:
                try:
                    if float(value) > 0:
                        return True
                except (TypeError, ValueError):
                    pass
            if _nested_positive_number_v41(value, keys):
                return True
    elif isinstance(response, list):
        return any(_nested_positive_number_v41(value, keys) for value in response)
    return False


def _has_logistics_result_v41(response: Any) -> bool:
    if not isinstance(response, dict):
        return False
    agents = response.get("agents_called")
    agents = agents if isinstance(agents, list) else []
    has_agent = any(str(agent).strip().lower() == "logistics_agent" for agent in agents)
    has_cbm = _nested_positive_number_v41(response, {"total_cbm", "shipment_cbm"})
    return has_agent and has_cbm


def should_attempt_llm(user_text: str, response: Any, local_corrections: list[str]) -> tuple[bool, str]:
    mode = _mode()
    if mode == "off":
        return False, "disabled"
    if mode == "always":
        return True, "always_mode"
    if local_corrections or _contains_probable_domain_typo(user_text):
        return True, "probable_typo"
    if not isinstance(response, dict):
        return True, "non_mapping_response"

    intent = str(response.get("detected_intent") or "").strip().lower()
    agents = response.get("agents_called")
    status = str(response.get("status") or response.get("decision") or "").lower()
    missing = _missing_items(response)

    if not intent or intent == "unknown":
        return True, "unknown_intent"
    if not isinstance(agents, list) or not agents:
        return True, "no_agent_route"
    if any(marker in " ".join(missing) for marker in ROUTE_MISSING_MARKERS):
        return True, "route_not_understood"
    if any(word in status for word in ("error", "failed", "unknown")):
        return True, "weak_status"
    if _looks_like_physical_shipment_v41(user_text):
        if intent != "logistics":
            return True, "physical_shipment_misrouted"
        if not _has_logistics_result_v41(response):
            return True, "physical_shipment_metrics_missing"
    return False, "deterministic_response_sufficient"


def _number_counter(text: str) -> Counter[str]:
    values: list[str] = []
    for match in re.finditer(r"(?<![A-Za-z0-9.])[-+]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)", text):
        token = match.group(0).replace(",", "")
        try:
            number = float(token)
        except ValueError:
            continue
        values.append(format(number, ".15g"))
    return Counter(values)


def _strip_json_fence(value: str) -> str:
    text = str(value or "").lstrip("\ufeff").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


# GEMINI_JSON_RESILIENCE_V43
def _extract_json_mapping_v43(value: str) -> dict[str, Any]:
    """Extract one JSON object without accepting invented or non-JSON facts."""
    text = _strip_json_fence(value)
    if not text:
        raise json.JSONDecodeError("empty Gemini response", text, 0)

    try:
        direct = json.loads(text)
        if isinstance(direct, dict):
            return direct
        raise TypeError("Gemini JSON root must be an object")
    except json.JSONDecodeError as first_error:
        decoder = json.JSONDecoder()
        for index, character in enumerate(text):
            if character != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                return candidate
        raise first_error


def _gemini_text_from_success_v43(data: Any) -> str:
    try:
        candidate = data["candidates"][0]
        content = candidate["content"]
        parts = content["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiInterpreterTransportError(
            f"invalid_success_payload_{type(exc).__name__}"
        ) from exc

    texts = [
        str(part.get("text"))
        for part in parts
        if isinstance(part, dict) and part.get("text") is not None
    ]
    joined = "".join(texts).strip()
    if not joined:
        finish_reason = str(candidate.get("finishReason") or "UNKNOWN")
        raise GeminiInterpreterTransportError(
            f"empty_success_text_{finish_reason}"
        )
    return joined


def _json_repair_prompt_v43(
    original_text: str,
    locally_normalized_text: str,
    malformed_output: str,
) -> str:
    previous = str(malformed_output or "")[-12000:]
    return (
        _prompt(original_text, locally_normalized_text)
        + "\n\nThe previous model response below was malformed or did not match the required schema. "
        + "Treat it only as draft data. Return one complete valid JSON object using the exact schema above. "
        + "Do not explain the correction, do not use Markdown fences, and do not add or alter any fact or number.\n\n"
        + "Previous malformed response:\n"
        + previous
    )


def _prompt(original_text: str, locally_normalized_text: str) -> str:
    return f"""You are a strict logistics request interpreter.

Your only job is to correct obvious spelling, punctuation, and sentence-order problems and return a structured interpretation. Do not calculate anything. Do not invent any fact. Do not add any number, unit, currency, country, product, route, Incoterm, cost, or handling property that the user did not state. Preserve every explicit number and unit exactly. Never convert a unit. If something is uncertain, keep it out of normalized_text and list it under ambiguities or missing_fields.

Make normalized_text easy for a deterministic shipment parser:
- express a route as "from ORIGIN to DESTINATION" when both were stated;
- separate dimensions with "x" while preserving every original value and unit;
- state quantity, package type, product, per-unit dimensions, per-unit weight and handling properties explicitly;
- put different cargo items in separate sentences;
- correct wording such as "dont stack" to "non-stackable" only when that meaning is explicit.

Return JSON only with this exact shape:
{{
  "normalized_text": "a clear natural-language rewrite",
  "intent": "logistics|shopping|document|finance|trader|compliance|general|unknown",
  "confidence": 0.0,
  "corrections": ["short descriptions"],
  "ambiguities": ["uncertain meanings"],
  "missing_fields": ["important unstated fields"],
  "shipment": {{
    "origin": null,
    "destination": null,
    "incoterm": null,
    "budget": null,
    "transport_mode": null,
    "items": [
      {{
        "name": null,
        "quantity": null,
        "package_type": null,
        "unit_weight_kg": null,
        "total_weight_kg": null,
        "total_cbm": null,
        "dimensions": null,
        "fragile": null,
        "stackable": null,
        "hazardous": null
      }}
    ]
  }}
}}

Original user text:
{original_text}

Conservatively normalized text:
{locally_normalized_text}
"""


def _gemini_credentials() -> tuple[str, str]:
    try:
        from app.smart_answer import get_gemini_api_key, get_gemini_model
        return get_gemini_api_key().strip(), get_gemini_model().strip()
    except Exception:
        return "", os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"


class GeminiInterpreterTransportError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _gemini_http_reason_v42(response: httpx.Response) -> str:
    status_name = "UNKNOWN"
    try:
        body = response.json()
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            status_name = str(error.get("status") or status_name)
    except Exception:
        pass
    safe_status = re.sub(r"[^A-Za-z0-9_-]+", "_", status_name).strip("_") or "UNKNOWN"
    return f"http_{response.status_code}_{safe_status}"


def _default_gemini_transport(*, prompt: str, api_key: str, model: str, timeout: float) -> str:
    global _CIRCUIT_OPEN_UNTIL
    now = time.monotonic()
    if now < _CIRCUIT_OPEN_UNTIL:
        remaining = max(1, int(round(_CIRCUIT_OPEN_UNTIL - now)))
        raise GeminiInterpreterTransportError(f"circuit_open_{remaining}s")

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "maxOutputTokens": 8192,
        },
    }

    retryable_statuses = {429, 500, 502, 503, 504}
    retry_delays = (0.0, 1.0, 2.0)
    last_error: Exception | None = None

    for attempt, delay in enumerate(retry_delays):
        if delay:
            time.sleep(delay)
        try:
            response = httpx.post(
                endpoint,
                params={"key": api_key},
                json=payload,
                timeout=timeout,
            )
        except (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        ) as exc:
            last_error = GeminiInterpreterTransportError(
                f"{type(exc).__name__}_attempt_{attempt + 1}"
            )
            continue

        if 200 <= response.status_code < 300:
            _CIRCUIT_OPEN_UNTIL = 0.0
            try:
                data = response.json()
            except ValueError as exc:
                raise GeminiInterpreterTransportError(
                    f"invalid_success_payload_{type(exc).__name__}"
                ) from exc
            return _gemini_text_from_success_v43(data)

        reason = _gemini_http_reason_v42(response)
        last_error = GeminiInterpreterTransportError(reason)
        if response.status_code not in retryable_statuses:
            raise last_error

        retry_after = response.headers.get("Retry-After")
        if retry_after and attempt + 1 < len(retry_delays):
            try:
                time.sleep(min(5.0, max(0.0, float(retry_after))))
            except (TypeError, ValueError):
                pass

    _CIRCUIT_OPEN_UNTIL = time.monotonic() + CIRCUIT_BREAK_SECONDS
    if last_error is not None:
        raise last_error
    raise GeminiInterpreterTransportError("unknown_transport_failure")


def interpret_with_llm(
    original_text: str,
    locally_normalized_text: str,
    *,
    transport: Callable[..., str] | None = None,
) -> InterpretationResult:
    api_key, model = _gemini_credentials()
    if transport is None and not api_key:
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=False,
            used_llm=False,
            reason="gemini_key_unavailable",
        )

    call = transport or _default_gemini_transport
    validation_reason = "validated_llm_rewrite"
    try:
        raw = call(
            prompt=_prompt(original_text, locally_normalized_text),
            api_key=api_key,
            model=model,
            timeout=_timeout_seconds(),
        )
        try:
            payload = LLMInterpretationPayload.model_validate(
                _extract_json_mapping_v43(raw)
            )
        except (ValidationError, json.JSONDecodeError, TypeError, ValueError):
            repaired_raw = call(
                prompt=_json_repair_prompt_v43(
                    original_text,
                    locally_normalized_text,
                    raw,
                ),
                api_key=api_key,
                model=model,
                timeout=_timeout_seconds(),
            )
            payload = LLMInterpretationPayload.model_validate(
                _extract_json_mapping_v43(repaired_raw)
            )
            validation_reason = "validated_llm_json_repair"
    except (ValidationError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            model=model,
            reason=f"invalid_llm_output_after_repair:{type(exc).__name__}",
        )
    except Exception as exc:
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            model=model,
            reason=(
                f"llm_unavailable:{getattr(exc, 'reason', type(exc).__name__)}"
            ),
        )

    effective = payload.normalized_text.strip()
    if not effective:
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            model=model,
            reason="empty_llm_rewrite",
        )

    original_numbers = _number_counter(original_text)
    rewritten_numbers = _number_counter(effective)
    if original_numbers != rewritten_numbers:
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            model=model,
            confidence=payload.confidence,
            reason="numeric_guard_rejected_rewrite",
            corrections=tuple(payload.corrections),
            ambiguities=tuple(payload.ambiguities),
            missing_fields=tuple(payload.missing_fields),
        )

    if payload.confidence < _min_confidence():
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            model=model,
            confidence=payload.confidence,
            reason="confidence_below_threshold",
            corrections=tuple(payload.corrections),
            ambiguities=tuple(payload.ambiguities),
            missing_fields=tuple(payload.missing_fields),
            structured_shipment=payload.shipment.model_dump(),
        )

    return InterpretationResult(
        original_text=original_text,
        effective_text=effective,
        attempted_llm=True,
        used_llm=True,
        provider="gemini",
        model=model,
        confidence=payload.confidence,
        reason=validation_reason,
        corrections=tuple(payload.corrections),
        ambiguities=tuple(payload.ambiguities),
        missing_fields=tuple(payload.missing_fields),
        structured_shipment=payload.shipment.model_dump(),
    )


def _attach_metadata(response: Any, result: InterpretationResult, chosen_text: str) -> Any:
    if not isinstance(response, dict):
        return response

    response["request_interpretation"] = result.metadata()
    metadata = response.get("request_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        response["request_metadata"] = metadata

    metadata["input_source"] = result.original_text
    metadata["original_input_source"] = result.original_text
    if chosen_text != result.original_text:
        metadata["interpreted_input_source"] = chosen_text
    metadata["interpretation_used_llm"] = result.used_llm
    metadata["interpretation_provider"] = result.provider
    metadata["interpretation_confidence"] = result.confidence
    metadata["interpretation_reason"] = result.reason
    return response


def run_with_interpreter(
    user_text: str,
    deterministic_runner: Callable[[str], Any],
    *,
    interpreter: Callable[[str, str], InterpretationResult] | None = None,
) -> Any:
    original = str(user_text or "").strip()
    if not original:
        return deterministic_runner(original)

    local_text, local_corrections = normalize_human_text(original)
    first_response = deterministic_runner(local_text)
    attempt, reason = should_attempt_llm(original, first_response, local_corrections)

    if not attempt:
        local_result = InterpretationResult(
            original_text=original,
            effective_text=local_text,
            reason=reason,
            corrections=tuple(local_corrections),
        )
        return _attach_metadata(first_response, local_result, local_text)

    llm_result = (
        interpreter(original, local_text)
        if interpreter is not None
        else interpret_with_llm(original, local_text)
    )

    if not llm_result.used_llm or llm_result.effective_text == local_text:
        merged = InterpretationResult(
            original_text=original,
            effective_text=local_text,
            attempted_llm=llm_result.attempted_llm,
            used_llm=False,
            provider=llm_result.provider,
            model=llm_result.model,
            confidence=llm_result.confidence,
            reason=llm_result.reason,
            corrections=tuple(local_corrections) + tuple(llm_result.corrections),
            ambiguities=llm_result.ambiguities,
            missing_fields=llm_result.missing_fields,
            structured_shipment=llm_result.structured_shipment,
        )
        return _attach_metadata(first_response, merged, local_text)

    second_response = deterministic_runner(llm_result.effective_text)
    if _response_quality(second_response) + 0.01 >= _response_quality(first_response):
        chosen_response = second_response
        chosen_text = llm_result.effective_text
        chosen_result = llm_result
    else:
        chosen_response = first_response
        chosen_text = local_text
        chosen_result = InterpretationResult(
            original_text=original,
            effective_text=local_text,
            attempted_llm=True,
            used_llm=False,
            provider=llm_result.provider,
            model=llm_result.model,
            confidence=llm_result.confidence,
            reason="deterministic_response_scored_higher",
            corrections=tuple(local_corrections) + tuple(llm_result.corrections),
            ambiguities=llm_result.ambiguities,
            missing_fields=llm_result.missing_fields,
            structured_shipment=llm_result.structured_shipment,
        )

    return _attach_metadata(chosen_response, chosen_result, chosen_text)

# PROMPT_ROBUSTNESS_BACKEND_GATE_HELPER_V41
def _run_deterministic_without_nested_llm_v41(
    deterministic_runner: Callable[[str], Any],
    text: str,
) -> Any:
    previous = os.environ.get("LLM_INTERPRETER_MODE")
    os.environ["LLM_INTERPRETER_MODE"] = "off"
    try:
        return deterministic_runner(text)
    finally:
        if previous is None:
            os.environ.pop("LLM_INTERPRETER_MODE", None)
        else:
            os.environ["LLM_INTERPRETER_MODE"] = previous


def _prefer_interpreted_response_v41(first: Any, second: Any, original_text: str) -> bool:
    if _looks_like_physical_shipment_v41(original_text):
        first_has_logistics = _has_logistics_result_v41(first)
        second_has_logistics = _has_logistics_result_v41(second)
        if second_has_logistics and not first_has_logistics:
            return True
        first_intent = str(first.get("detected_intent") or "").lower() if isinstance(first, dict) else ""
        second_intent = str(second.get("detected_intent") or "").lower() if isinstance(second, dict) else ""
        if second_intent == "logistics" and first_intent != "logistics":
            return True
    return _response_quality(second) + 0.01 >= _response_quality(first)


# LOCAL_STRUCTURED_SHIPMENT_REPAIR_V42
# A strict, calculation-only fallback for clearly stated physical shipments.
# It handles common spelling/punctuation/order mistakes without depending on
# network availability. Gemini remains the fallback for language that cannot be
# safely resolved from explicit quantities, dimensions, units, route and weight.
_V42_WEIGHT_UNIT = r"(?:kilograms?|kgs?|kg|pounds?|lbs?|lb)"
_V42_PACKAGE = r"(?:crates?|pallets?|boxes?|packs?|cartons?|units?)"
_V42_COUNTRY_MAP = {
    "united states of america": "USA",
    "united states": "USA",
    "usa": "USA",
    "us": "USA",
    "united kingdom": "UK",
    "uk": "UK",
    "uae": "UAE",
    "turkiye": "Turkey",
    "india": "India",
    "germany": "Germany",
    "france": "France",
    "canada": "Canada",
    "china": "China",
    "zambia": "Zambia",
    "finland": "Finland",
    "spain": "Spain",
    "portugal": "Portugal",
    "italy": "Italy",
    "netherlands": "Netherlands",
    "mexico": "Mexico",
    "japan": "Japan",
    "south korea": "South Korea",
    "singapore": "Singapore",
    "australia": "Australia",
    "iran": "Iran",
    "turkey": "Turkey",
}
_V42_COUNTRY = "(?:" + "|".join(
    sorted((re.escape(value) for value in _V42_COUNTRY_MAP), key=len, reverse=True)
) + ")"
_V42_LENGTH_FACTORS = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "metre": 1.0,
    "metres": 1.0,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "centimetre": 0.01,
    "centimetres": 0.01,
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "millimetre": 0.001,
    "millimetres": 0.001,
    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
}


def _v42_number_text(value: float) -> str:
    rounded = round(float(value), 6)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.6f}".rstrip("0").rstrip(".")


def _v42_clean_item_name(value: str) -> str:
    text = str(value or "").lower().strip(" ,.;:-")
    text = re.sub(r"^(?:ship|send|need\s+send|export|import)\s+", "", text)
    text = re.sub(r"\b(?:fragile|but|stackable|non[- ]stackable|do not stack|not fragile)\b", " ", text)
    text = re.sub(r"\b(?:exw|fca|fas|fob|cfr|cif|cpt|cip|dap|dpu|ddp)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _v42_route(text: str) -> tuple[str | None, str | None, tuple[int, int] | None]:
    raw = str(text or "")
    direct = re.search(
        rf"\bfrom\s+(?P<origin>{_V42_COUNTRY})\s+to\s+(?P<destination>{_V42_COUNTRY})\b",
        raw,
        flags=re.IGNORECASE,
    )
    if direct:
        return (
            _V42_COUNTRY_MAP[direct.group("origin").lower()],
            _V42_COUNTRY_MAP[direct.group("destination").lower()],
            direct.span(),
        )

    origin = re.search(rf"\borigin\s+(?P<value>{_V42_COUNTRY})\b", raw, flags=re.IGNORECASE)
    destination = re.search(rf"\bdestination\s+(?P<value>{_V42_COUNTRY})\b", raw, flags=re.IGNORECASE)
    if origin and destination:
        return (
            _V42_COUNTRY_MAP[origin.group("value").lower()],
            _V42_COUNTRY_MAP[destination.group("value").lower()],
            (min(origin.start(), destination.start()), max(origin.end(), destination.end())),
        )

    shorthand = re.search(
        rf"\b(?P<origin>{_V42_COUNTRY})\s+to\s+(?P<destination>{_V42_COUNTRY})\b",
        raw,
        flags=re.IGNORECASE,
    )
    if shorthand:
        return (
            _V42_COUNTRY_MAP[shorthand.group("origin").lower()],
            _V42_COUNTRY_MAP[shorthand.group("destination").lower()],
            shorthand.span(),
        )
    return None, None, None


def _v42_dimensions(text: str) -> tuple[dict[str, float], tuple[int, int]] | None:
    match = re.search(
        rf"(?P<a>{_V41_NUMBER})\s*(?P<ua>{_V41_LENGTH_UNIT})\s*x\s*"
        rf"(?P<b>{_V41_NUMBER})\s*(?P<ub>{_V41_LENGTH_UNIT})\s*x\s*"
        rf"(?P<c>{_V41_NUMBER})\s*(?P<uc>{_V41_LENGTH_UNIT})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    values = []
    for value_group, unit_group in (("a", "ua"), ("b", "ub"), ("c", "uc")):
        number = float(match.group(value_group))
        unit = match.group(unit_group).lower()
        factor = _V42_LENGTH_FACTORS.get(unit)
        if factor is None:
            return None
        values.append(number * factor)

    return (
        {
            "length_m": round(values[0], 6),
            "width_m": round(values[1], 6),
            "height_m": round(values[2], 6),
        },
        match.span(),
    )


def _v42_unit_weight_kg(text: str) -> float | None:
    patterns = [
        rf"\b(?:weighs?|weight(?:\s+is)?|wt)\s*(?P<value>{_V41_NUMBER})\s*(?P<unit>{_V42_WEIGHT_UNIT})\b",
        rf"(?P<value>{_V41_NUMBER})\s*(?P<unit>{_V42_WEIGHT_UNIT})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit.startswith("lb") or unit.startswith("pound"):
            value *= 0.45359237
        return round(value, 6)
    return None


def _v42_item(clause: str) -> dict[str, Any] | None:
    quantity: int | None = None
    package_type: str | None = None
    item_name: str | None = None

    leading = re.search(
        rf"\b(?P<quantity>\d+)\s+"
        rf"(?P<prefix>(?:[A-Za-z-]+\s+){{0,2}})?"
        rf"(?P<package>{_V42_PACKAGE})\b"
        rf"(?P<tail>.*?)(?=\beach\b|$)",
        clause,
        flags=re.IGNORECASE,
    )
    if leading:
        quantity = int(leading.group("quantity"))
        package_type = leading.group("package").lower()
        tail = str(leading.group("tail") or "").strip()
        prefix = str(leading.group("prefix") or "").strip()
        if tail.lower().startswith("each"):
            tail = ""
        cleaned_tail = _v42_clean_item_name(tail)
        item_name = cleaned_tail or _v42_clean_item_name(f"{prefix} {package_type}")

    if quantity is None:
        quantity_match = re.search(
            r"\bquantity\s*(?:is|=|:)?\s*(?P<quantity>\d+)\b",
            clause,
            flags=re.IGNORECASE,
        )
        package_match = re.search(
            rf"\beach\s+(?P<package>{_V42_PACKAGE})\b",
            clause,
            flags=re.IGNORECASE,
        )
        if quantity_match and package_match:
            quantity = int(quantity_match.group("quantity"))
            package_type = package_match.group("package").lower()
            item_name = _v42_clean_item_name(clause[: package_match.start()])

    dimensions_result = _v42_dimensions(clause)
    unit_weight_kg = _v42_unit_weight_kg(clause)
    if not quantity or not package_type or not item_name or not dimensions_result or unit_weight_kg is None:
        return None

    dimensions, _ = dimensions_result
    unit_cbm = (
        dimensions["length_m"]
        * dimensions["width_m"]
        * dimensions["height_m"]
    )
    total_cbm = unit_cbm * quantity
    total_weight_kg = unit_weight_kg * quantity

    lowered = clause.lower()
    fragile = "fragile" in lowered and "not fragile" not in lowered
    non_stackable = any(
        marker in lowered
        for marker in ("do not stack", "non-stackable", "non stackable", "not stackable")
    )
    stackable = "stackable" in lowered and not non_stackable

    return {
        "name": item_name,
        "quantity": quantity,
        "package_type": package_type,
        "dimensions_m": dimensions,
        "unit_cbm": round(unit_cbm, 6),
        "total_cbm": round(total_cbm, 6),
        "unit_weight_kg": round(unit_weight_kg, 6),
        "total_weight_kg": round(total_weight_kg, 6),
        "fragile": fragile,
        "stackable": stackable,
    }


def _v42_local_shipment_repair(original: str, normalized: str) -> dict[str, Any] | None:
    if not _looks_like_physical_shipment_v41(normalized):
        return None

    origin, destination, route_span = _v42_route(normalized)
    if not origin or not destination:
        return None

    cargo_text = normalized
    if route_span:
        cargo_text = normalized[: route_span[0]] + " " + normalized[route_span[1] :]

    clauses = re.split(r"\s+and\s+(?=\d+\s+)", cargo_text, flags=re.IGNORECASE)
    items = [_v42_item(clause) for clause in clauses]
    if not items or any(item is None for item in items):
        return None
    resolved_items = [item for item in items if isinstance(item, dict)]

    total_cbm = round(sum(float(item["total_cbm"]) for item in resolved_items), 6)
    total_weight_kg = round(sum(float(item["total_weight_kg"]) for item in resolved_items), 6)
    incoterm_match = re.search(
        r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    incoterm = incoterm_match.group(1).upper() if incoterm_match else None

    item_phrases: list[str] = []
    detail_sentences: list[str] = []
    for item in resolved_items:
        quantity = int(item["quantity"])
        package_type = str(item["package_type"])
        name = str(item["name"])
        package_singular = package_type[:-1] if package_type.endswith("s") else package_type
        if package_type.rstrip("s") in name.lower().split():
            item_phrases.append(f"{quantity} {name}")
        else:
            item_phrases.append(f"{quantity} {package_type} of {name}")

        dimensions = item["dimensions_m"]
        detail = (
            f"Each {package_singular} of {name} measures "
            f"{_v42_number_text(dimensions['length_m'])} m x "
            f"{_v42_number_text(dimensions['width_m'])} m x "
            f"{_v42_number_text(dimensions['height_m'])} m and weighs "
            f"{_v42_number_text(item['unit_weight_kg'])} kg"
        )
        handling: list[str] = []
        if item.get("fragile"):
            handling.append("fragile")
        if item.get("stackable") is False:
            handling.append("non-stackable")
        elif item.get("stackable") is True:
            handling.append("stackable")
        if handling:
            detail += "; it is " + " and ".join(handling)
        detail_sentences.append(detail + ".")

    if len(item_phrases) == 1:
        cargo_phrase = item_phrases[0]
    else:
        cargo_phrase = ", ".join(item_phrases[:-1]) + " and " + item_phrases[-1]

    canonical_parts = [
        f"Ship {cargo_phrase} from {origin} to {destination}.",
        f"Total shipment volume is {_v42_number_text(total_cbm)} CBM.",
        f"Total shipment weight is {_v42_number_text(total_weight_kg)} kg.",
    ]
    if incoterm:
        canonical_parts.append(f"Use {incoterm} Incoterm.")
    canonical_parts.extend(detail_sentences)

    return {
        "canonical_text": " ".join(canonical_parts),
        "origin": origin,
        "destination": destination,
        "incoterm": incoterm,
        "items": resolved_items,
        "total_cbm": total_cbm,
        "total_weight_kg": total_weight_kg,
        "cargo_units": sum(int(item["quantity"]) for item in resolved_items),
        "calculation_source": "explicit_quantity_dimensions_and_unit_weight",
    }


def _v42_apply_local_facts(response: Any, facts: dict[str, Any]) -> Any:
    if not isinstance(response, dict):
        return response

    response["detected_intent"] = "logistics"
    agents = response.get("agents_called")
    agents = list(agents) if isinstance(agents, list) else []
    if "logistics_agent" not in {str(agent).lower() for agent in agents}:
        agents.append("logistics_agent")
    response["agents_called"] = agents

    metrics = response.get("logistics_metrics")
    metrics = dict(metrics) if isinstance(metrics, dict) else {}
    metrics.update(
        {
            "total_cbm": facts["total_cbm"],
            "total_weight_kg": facts["total_weight_kg"],
            "cargo_units": facts["cargo_units"],
            "item_count": len(facts["items"]),
        }
    )
    response["logistics_metrics"] = metrics

    handoff = response.get("handoff_payload")
    handoff = dict(handoff) if isinstance(handoff, dict) else {}
    handoff.update(
        {
            "origin": facts["origin"],
            "destination": facts["destination"],
            "total_cbm": facts["total_cbm"],
            "total_weight_kg": facts["total_weight_kg"],
            "cargo_units": facts["cargo_units"],
        }
    )
    response["handoff_payload"] = handoff
    response["local_shipment_facts"] = facts
    return response


def run_backend_with_interpreter(
    user_text: str,
    deterministic_runner: Callable[[str], Any],
    *,
    interpreter: Callable[[str, str], InterpretationResult] | None = None,
) -> Any:
    """Own the LLM gate at the final backend boundary used by the API/frontend."""
    original = str(user_text or "").strip()
    if not original:
        return _run_deterministic_without_nested_llm_v41(deterministic_runner, original)

    local_text, local_corrections = normalize_human_text(original)
    mode = _mode()

    if mode == "off":
        # Off mode must be completely transparent. This is used by the full
        # regression suite and by operators who explicitly disable the
        # interpreter. Do not even apply local typo/punctuation normalization,
        # because legacy deterministic parsers may rely on the original form.
        response = _run_deterministic_without_nested_llm_v41(deterministic_runner, original)
        result = InterpretationResult(
            original_text=original,
            effective_text=original,
            reason="disabled",
            corrections=(),
        )
        return _attach_metadata(response, result, original)

    # Resolve complete, explicitly stated physical shipments locally first. This
    # is deterministic and remains available during Gemini outages or quotas.
    if mode == "fallback":
        local_facts = _v42_local_shipment_repair(original, local_text)
        if local_facts is not None:
            canonical_text = str(local_facts["canonical_text"])
            repaired_response = _run_deterministic_without_nested_llm_v41(
                deterministic_runner,
                canonical_text,
            )
            repaired_response = _v42_apply_local_facts(repaired_response, local_facts)
            result = InterpretationResult(
                original_text=original,
                effective_text=canonical_text,
                attempted_llm=False,
                used_llm=False,
                provider="deterministic",
                confidence=1.0,
                reason="local_structured_repair",
                corrections=tuple(local_corrections),
                structured_shipment=local_facts,
            )
            return _attach_metadata(repaired_response, result, canonical_text)

    # Obvious typo cases can be interpreted before spending time on a known-weak run.
    pre_reason = None
    if mode == "always":
        pre_reason = "always_mode"
    elif local_corrections or _contains_probable_domain_typo(original):
        pre_reason = "probable_typo"

    first_response = None
    if pre_reason is None:
        first_response = _run_deterministic_without_nested_llm_v41(deterministic_runner, local_text)
        attempt, reason = should_attempt_llm(original, first_response, local_corrections)
        if not attempt:
            result = InterpretationResult(
                original_text=original,
                effective_text=local_text,
                reason=reason,
                corrections=tuple(local_corrections),
            )
            return _attach_metadata(first_response, result, local_text)
    else:
        reason = pre_reason

    llm_result = (
        interpreter(original, local_text)
        if interpreter is not None
        else interpret_with_llm(original, local_text)
    )

    if not llm_result.used_llm or llm_result.effective_text == local_text:
        if first_response is None:
            first_response = _run_deterministic_without_nested_llm_v41(deterministic_runner, local_text)
        merged = InterpretationResult(
            original_text=original,
            effective_text=local_text,
            attempted_llm=llm_result.attempted_llm,
            used_llm=False,
            provider=llm_result.provider,
            model=llm_result.model,
            confidence=llm_result.confidence,
            reason=llm_result.reason or reason,
            corrections=tuple(local_corrections) + tuple(llm_result.corrections),
            ambiguities=llm_result.ambiguities,
            missing_fields=llm_result.missing_fields,
            structured_shipment=llm_result.structured_shipment,
        )
        return _attach_metadata(first_response, merged, local_text)

    interpreted_response = _run_deterministic_without_nested_llm_v41(
        deterministic_runner,
        llm_result.effective_text,
    )

    if first_response is None or _prefer_interpreted_response_v41(
        first_response,
        interpreted_response,
        original,
    ):
        return _attach_metadata(interpreted_response, llm_result, llm_result.effective_text)

    rejected = InterpretationResult(
        original_text=original,
        effective_text=local_text,
        attempted_llm=True,
        used_llm=False,
        provider=llm_result.provider,
        model=llm_result.model,
        confidence=llm_result.confidence,
        reason="deterministic_response_scored_higher",
        corrections=tuple(local_corrections) + tuple(llm_result.corrections),
        ambiguities=llm_result.ambiguities,
        missing_fields=llm_result.missing_fields,
        structured_shipment=llm_result.structured_shipment,
    )
    return _attach_metadata(first_response, rejected, local_text)
