from __future__ import annotations

from app.text_request_intent import classify_text_request_intent

import json
from pathlib import Path
from typing import Any


SHOPPING_KEYWORDS = {
    "buy",
    "source",
    "supplier",
    "suppliers",
    "shopping",
    "purchase",
    "order",
    "budget",
    "prefer suppliers",
    "avoid",
}

DOCUMENT_KEYWORDS = {
    "invoice",
    "packing list",
    "bill of lading",
    "certificate of origin",
    "document",
    "documents",
}

LOGISTICS_KEYWORDS = {
    "shipment",
    "shipping",
    "container",
    "cbm",
    "cargo",
    "freight",
    "lcl",
    "fcl",
    "fit",
    "loading",
    "packaging",
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


# RULE_ROUTER_FALLBACK_V45: use the richer deterministic classifier only when keyword scores are zero.
def detect_text_intent(text: str) -> dict[str, Any]:
    normalized = _normalize(text)

    scores = {
        "shopping": sum(1 for keyword in SHOPPING_KEYWORDS if keyword in normalized),
        "document": sum(1 for keyword in DOCUMENT_KEYWORDS if keyword in normalized),
        "logistics": sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in normalized),
    }

    detected_intent = max(scores, key=scores.get)

    if scores[detected_intent] == 0:
        fallback_intent = classify_text_request_intent(normalized)
        if fallback_intent in scores and fallback_intent != "unknown":
            detected_intent = fallback_intent
            scores[fallback_intent] = 1
        else:
            detected_intent = "unknown"

    return {
        "detected_intent": detected_intent,
        "scores": scores,
        "source": "text",
    }


def detect_file_intent(paths: list[str | Path]) -> dict[str, Any]:
    path_objects = [Path(path) for path in paths]
    suffixes = {path.suffix.lower() for path in path_objects}

    if suffixes.intersection({".txt", ".pdf", ".docx"}):
        return {
            "detected_intent": "document",
            "scores": {
                "document": 1,
                "shopping": 0,
                "logistics": 0,
            },
            "source": "files",
        }

    return {
        "detected_intent": "unknown",
        "scores": {
            "document": 0,
            "shopping": 0,
            "logistics": 0,
        },
        "source": "files",
    }


def detect_json_intent(data: dict[str, Any]) -> dict[str, Any]:
    items = data.get("items", [])
    has_preferences = "preferences" in data
    has_destination_country = "destination_country" in data
    has_origin_destination = "origin" in data and "destination" in data

    item_keys = set()
    for item in items:
        if isinstance(item, dict):
            item_keys.update(item.keys())

    logistics_keys = {
        "length",
        "width",
        "height",
        "length_cm",
        "width_cm",
        "height_cm",
        "weight",
        "weight_kg",
        "unit_weight_kg",
        "dimensions",
        "cbm",
        "quantity",
    }

    if has_origin_destination and item_keys.intersection(logistics_keys):
        detected_intent = "logistics"
    elif has_preferences or has_destination_country:
        detected_intent = "shopping"
    elif items:
        detected_intent = "shopping"
    else:
        detected_intent = "unknown"

    return {
        "detected_intent": detected_intent,
        "scores": {
            "shopping": 1 if detected_intent == "shopping" else 0,
            "logistics": 1 if detected_intent == "logistics" else 0,
            "document": 0,
        },
        "source": "json",
    }


def read_json_file(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as file:
        return json.load(file)


# Text fallback added for procurement/logistics-style natural language requests.
# It preserves the original router result unless the original router returns unknown.
try:
    _original_detect_intent_for_text_fallback = detect_intent

    def detect_intent(user_text):
        detected_intent = _original_detect_intent_for_text_fallback(user_text)

        if detected_intent in {None, "", "unknown"}:
            fallback_intent = classify_text_request_intent(str(user_text))

            if fallback_intent != "unknown":
                return fallback_intent

        return detected_intent

except NameError:
    pass

# SHIPPING_INTENT_GUARDRAIL_V48
import re as _re

_detect_text_intent_before_shipping_guardrail_v48 = detect_text_intent


def _v48_explicit_shipping_signal(text: str) -> bool:
    normalized = _normalize(text)
    active_shipping = _re.search(
        r"\b(?:ship|shipping|send|sending|freight|transport|book)\b",
        normalized,
        flags=_re.IGNORECASE,
    )
    # Do not treat a bare origin/destination phrase as proof of shipping.
    # Requests such as "I need 50 TVs from India to USA under FOB terms" are
    # established procurement requests and must remain Shopping Agent work.
    # The guardrail only corrects intent when an explicit shipping action is used.
    return bool(active_shipping)


def _v48_explicit_shopping_signal(text: str) -> bool:
    normalized = _normalize(text)
    return bool(
        _re.search(
            r"\b(?:supplier|suppliers|vendor|vendors|procure|procurement|purchase|buy|sourcing)\b",
            normalized,
            flags=_re.IGNORECASE,
        )
        or _re.search(
            r"\b(?:find|compare|source)\s+(?:me\s+)?(?:some\s+)?(?:supplier|suppliers|vendor|vendors)\b",
            normalized,
            flags=_re.IGNORECASE,
        )
        or _re.search(
            r"\bcompare\b.{0,40}\b(?:price|quality|supplier|vendor)\b",
            normalized,
            flags=_re.IGNORECASE,
        )
    )


def detect_text_intent(text: str) -> dict[str, Any]:
    result = _detect_text_intent_before_shipping_guardrail_v48(text)
    if not isinstance(result, dict):
        return result

    if _v48_explicit_shipping_signal(text) and not _v48_explicit_shopping_signal(text):
        result = dict(result)
        scores = dict(result.get("scores") or {})
        scores["logistics"] = max(1, int(scores.get("logistics") or 0))
        result["scores"] = scores
        result["detected_intent"] = "logistics"
        # Preserve the established V45 router-source contract. The guardrail
        # corrects intent only; it is not a separate routing backend.
        result.setdefault("source", "text")

    return result
