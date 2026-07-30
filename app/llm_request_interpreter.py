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
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MIN_CONFIDENCE = 0.65
CIRCUIT_BREAK_SECONDS = 300.0

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
        data.pop("effective_text", None)
        return data


TYPO_REPLACEMENTS = {
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
    return False, "deterministic_response_sufficient"


def _number_counter(text: str) -> Counter[str]:
    values: list[str] = []
    for match in re.finditer(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?", text):
        token = match.group(0).replace(",", "")
        try:
            number = float(token)
        except ValueError:
            continue
        values.append(format(number, ".15g"))
    return Counter(values)


def _strip_json_fence(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _prompt(original_text: str, locally_normalized_text: str) -> str:
    return f"""You are a strict logistics request interpreter.

Your only job is to correct obvious spelling, punctuation, and sentence-order problems and return a structured interpretation. Do not calculate anything. Do not invent any fact. Do not add any number, unit, currency, country, product, route, Incoterm, cost, or handling property that the user did not state. Preserve every explicit number and unit exactly. If something is uncertain, keep it out of normalized_text and list it under ambiguities or missing_fields.

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


def _default_gemini_transport(*, prompt: str, api_key: str, model: str, timeout: float) -> str:
    global _CIRCUIT_OPEN_UNTIL
    now = time.monotonic()
    if now < _CIRCUIT_OPEN_UNTIL:
        raise RuntimeError("Gemini interpreter circuit breaker is temporarily open")

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = httpx.post(endpoint, params={"key": api_key}, json=payload, timeout=timeout)
        if response.status_code in {429, 500, 502, 503, 504}:
            _CIRCUIT_OPEN_UNTIL = time.monotonic() + CIRCUIT_BREAK_SECONDS
        response.raise_for_status()
        data = response.json()
        return str(data["candidates"][0]["content"]["parts"][0]["text"])
    except Exception:
        raise


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
    try:
        raw = call(
            prompt=_prompt(original_text, locally_normalized_text),
            api_key=api_key,
            model=model,
            timeout=_timeout_seconds(),
        )
        payload = LLMInterpretationPayload.model_validate(json.loads(_strip_json_fence(raw)))
    except (ValidationError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            model=model,
            reason=f"invalid_llm_output:{type(exc).__name__}",
        )
    except Exception as exc:
        return InterpretationResult(
            original_text=original_text,
            effective_text=locally_normalized_text,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            model=model,
            reason=f"llm_unavailable:{type(exc).__name__}",
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
        reason="validated_llm_rewrite",
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
