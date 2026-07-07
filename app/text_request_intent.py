from __future__ import annotations

import re


SHOPPING_MARKERS = {
    "buy",
    "purchase",
    "procure",
    "supplier",
    "suppliers",
    "source",
    "sourcing",
    "quote",
    "quotes",
    "rfq",
    "budget",
    "prefer suppliers",
    "avoid",
}

LOGISTICS_MARKERS = {
    "ship",
    "shipment",
    "freight",
    "container",
    "cbm",
    "pallet",
    "warehouse",
    "port",
    "delivery",
    "transport",
    "move cargo",
}

DOCUMENT_MARKERS = {
    "invoice",
    "packing list",
    "bill of lading",
    "document",
    "documents",
    "customs document",
}

PRODUCT_WORDS = {
    "tv",
    "tvs",
    "television",
    "scooter",
    "scooters",
    "tiles",
    "ceramic",
    "laptop",
    "phones",
    "machinery",
    "cartons",
    "units",
    "boxes",
}


def _contains_any(text: str, markers: set[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _has_quantity_product_pattern(text: str) -> bool:
    lowered = text.lower()

    if re.search(r"\b\d+\s+[a-zA-Z][a-zA-Z0-9_-]*", lowered):
        return True

    return False


def _has_origin_destination_pattern(text: str) -> bool:
    lowered = text.lower()
    return " from " in f" {lowered} " and " to " in f" {lowered} "


def _has_product_word(text: str) -> bool:
    lowered_words = set(
        re.sub(r"[^a-zA-Z0-9\s_-]", " ", text.lower()).split()
    )

    return bool(lowered_words.intersection(PRODUCT_WORDS))


def classify_text_request_intent(user_text: str) -> str:
    text = str(user_text or "").strip()

    if not text:
        return "unknown"

    lowered = text.lower()

    if _contains_any(lowered, DOCUMENT_MARKERS):
        return "document"

    has_shopping_marker = _contains_any(lowered, SHOPPING_MARKERS)
    has_logistics_marker = _contains_any(lowered, LOGISTICS_MARKERS)
    has_quantity_product = _has_quantity_product_pattern(lowered)
    has_origin_destination = _has_origin_destination_pattern(lowered)
    has_product_word = _has_product_word(lowered)

    if has_shopping_marker:
        return "shopping"

    if has_logistics_marker and has_origin_destination:
        return "logistics"

    if has_logistics_marker:
        return "logistics"

    if has_quantity_product and has_product_word:
        return "shopping"

    if has_quantity_product and has_origin_destination:
        return "shopping"

    return "unknown"
