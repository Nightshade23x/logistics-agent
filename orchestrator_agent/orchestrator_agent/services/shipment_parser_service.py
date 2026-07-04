"""Parses free-text shipment queries into structured fields using Gemini."""

import json
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

class ShipmentParserService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def parse(self, query: str) -> ParsedShipment:
        raw = self._llm.generate(SYSTEM_PROMPT, query)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        return ParsedShipment(**data)