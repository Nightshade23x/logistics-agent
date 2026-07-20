"""Parses free-text shipment queries into structured shipment fields.

Gemini is used when available. If Gemini is unavailable, rate-limited, or
returns invalid JSON, the service falls back to deterministic regex extraction
so the orchestrator can still return a structured response instead of HTTP 500.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..shared_llm_client import LLMProvider
from ..schemas.shipment_request import ParsedShipment

SYSTEM_PROMPT = (
    "Extract shipment details from the user's message. Respond with ONLY a "
    "JSON object with these exact keys: product_description (string), "
    "country_from (string), country_to (string), target_market (string, "
    "usually same as country_to), quantity (integer or null), "
    "cargo_value (number, your best estimate of total shipment value in USD "
    "based on the product and quantity if not explicitly stated -- never "
    "return null or 0 for this field), weight_kg (number, your best estimate "
    "of total shipment weight in kg based on product and quantity), "
    "volume_m3 (number, your best estimate of total shipment volume in cubic "
    "meters), currency (string, default 'USD'). No other text, no markdown "
    "fences. Mark any estimated fields honestly -- these are approximations "
    "for planning purposes, not verified figures."
)


def _first_match(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        for group in match.groups():
            if group:
                return group.strip(" .,:;")
    return None


def _number_match(patterns: list[str], text: str) -> float | None:
    raw = _first_match(patterns, text)
    if raw is None:
        return None

    cleaned = raw.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _int_match(patterns: list[str], text: str) -> int | None:
    value = _number_match(patterns, text)
    if value is None:
        return None
    return int(value)


def _fallback_parse(query: str) -> dict[str, Any]:
    """Best-effort parser for common demo/integration shipment prompts."""
    quantity = _int_match(
        [
            r"\bship\s+(\d+)\b",
            r"\bsend\s+(\d+)\b",
            r"\bexport\s+(\d+)\b",
            r"\bimport\s+(\d+)\b",
            r"\bquantity\s*(?:is|=|:)\s*(\d+)\b",
        ],
        query,
    )

    product = _first_match(
        [
            r"\bship\s+\d+\s+(.+?)\s+from\s+[A-Za-z ]+\s+to\s+[A-Za-z ]+",
            r"\bsend\s+\d+\s+(.+?)\s+from\s+[A-Za-z ]+\s+to\s+[A-Za-z ]+",
            r"\bexport\s+\d+\s+(.+?)\s+from\s+[A-Za-z ]+\s+to\s+[A-Za-z ]+",
            r"\bimport\s+\d+\s+(.+?)\s+from\s+[A-Za-z ]+\s+to\s+[A-Za-z ]+",
            r"\bproduct(?: description)?\s*(?:is|=|:)\s*([A-Za-z0-9 ,\-/]+)",
        ],
        query,
    )

    country_from = _first_match(
        [
            r"\bcountry_from\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\borigin country\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\borigin\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bfrom\s+([A-Za-z ]+)\s+to\s+[A-Za-z ]+",
        ],
        query,
    )

    country_to = _first_match(
        [
            r"\bcountry_to\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bdestination country\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bdestination\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bto\s+([A-Za-z ]+)(?:\.|,|$)",
        ],
        query,
    )

    target_market = _first_match(
        [
            r"\btarget market\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bmarket\s*(?:is|=|:)\s*([A-Za-z ]+)",
        ],
        query,
    )

    cargo_value = _number_match(
        [
            r"\bcargo value\s*(?:is|=|:)\s*([0-9,.]+)",
            r"\bdeclared value\s*(?:is|=|:)\s*([0-9,.]+)",
            r"\bvalue\s*(?:is|=|:)\s*([0-9,.]+)",
        ],
        query,
    )

    weight_kg = _number_match(
        [
            r"\bweight(?:_kg)?\s*(?:is|=|:)\s*([0-9,.]+)\s*(?:kg|kilograms?)?",
            r"\b([0-9,.]+)\s*(?:kg|kilograms?)\b",
        ],
        query,
    )

    volume_m3 = _number_match(
        [
            r"\bvolume(?:_m3)?\s*(?:is|=|:)\s*([0-9,.]+)\s*(?:m3|cbm|cubic meters?)?",
            r"\b([0-9,.]+)\s*(?:m3|cbm|cubic meters?)\b",
        ],
        query,
    )

    currency = _first_match(
        [
            r"\bcurrency\s*(?:is|=|:)\s*([A-Z]{3})",
            r"\b(USD|EUR|GBP|INR|ZMW)\b",
        ],
        query,
    )

    data = {
        "product_description": product or "Unknown product",
        "country_from": country_from or "Unknown origin",
        "country_to": country_to or target_market or "Unknown destination",
        "target_market": target_market or country_to or "Unknown destination",
        "quantity": quantity,
        "cargo_value": cargo_value or 1.0,
        "weight_kg": weight_kg or 1.0,
        "volume_m3": volume_m3 or 0.01,
        "currency": currency or "USD",
    }

    return data


class ShipmentParserService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def parse(self, query: str) -> ParsedShipment:
        try:
            raw = self._llm.generate(SYSTEM_PROMPT, query)
            cleaned = (
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            data = json.loads(cleaned)
            return ParsedShipment(**data)
        except Exception:
            return ParsedShipment(**_fallback_parse(query))
