from __future__ import annotations

import re
from typing import Any


_SPLIT_PATTERN = re.compile(r"\s*(?:,|;|\band\b)\s*", re.IGNORECASE)

_CBM_PATTERN = re.compile(
    r"^(?:(?:estimate\s+freight\s+for|ship|send|export|import)\s+)?"
    r"(?P<cbm>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>cbm|m3|m\^3|cubic meters?|cubic metres?|ft3|ft\^3|cubic feet|cubic foot)"
    r"\s+(?:of\s+)?(?P<name>.+)$",
    re.IGNORECASE,
)

_QUANTITY_PATTERN = re.compile(
    r"^(?:(?:find\s+suppliers?\s+for|source\s+suppliers?\s+for|get\s+suppliers?\s+for|"
    r"estimate\s+freight\s+for|ship|send|export|import)\s+)?"
    r"(?P<quantity>\d+)\s+(?P<name>.+)$",
    re.IGNORECASE,
)

_RATE_ONLY_NAMES = {
    "percent",
    "percentage",
    "per cent",
    "%",
}

_FIELD_REMOVAL_PATTERNS = [
    r"\buse\s+(?:the\s+)?(?:incoterm\s+)?(?:EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\s+incoterm\b",
    r"\bincoterm\s*(?:is|=|:)\s*(?:EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b",
    r"\bfreight\s+quote\s*(?:is|=|:)\s*[$]?[0-9,.]+\s*(?:USD|dollars?)?\b",
    r"\binsurance\s+premium\s*(?:is|=|:)\s*[$]?[0-9,.]+\s*(?:USD|dollars?)?\b",
    r"\bduty\s+rate\s*(?:is|=|:)\s*[0-9,.]+\s*(?:%|percent|per\s+cent)\b",
    r"\bimport\s+tax\s+rate\s*(?:is|=|:)\s*[0-9,.]+\s*(?:%|percent|per\s+cent)\b",
    r"\btax\s+rate\s*(?:is|=|:)\s*[0-9,.]+\s*(?:%|percent|per\s+cent)\b",
    r"\bbudget\s*(?:is|=|:)\s*[$]?[0-9,.]+\s*(?:USD|dollars?)?\b",
]


def _clean_item_name(name: str) -> str:
    cleaned = name.strip().strip(".").strip()

    cleaned = re.sub(
        r"^(?:find\s+suppliers?\s+for|source\s+suppliers?\s+for|get\s+suppliers?\s+for|"
        r"estimate\s+freight\s+for|ship|send|export|import)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s+from\s+[A-Za-z ]+\s+to\s+[A-Za-z ]+(?:\.|,|;|$).*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.split(r"\.(?:\s|$)", cleaned, maxsplit=1)[0]
    return cleaned.strip().strip(".").strip()


def _clean_number(value: str) -> float:
    return float(value.replace(",", "").strip())


def _first_number(patterns: list[str], text: str) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_number(match.group(1))
    return None


def _first_text(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;")
    return None


def _extract_route(text: str) -> dict[str, str]:
    route: dict[str, str] = {}

    country_from = _first_text(
        [
            r"\bcountry_from\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\borigin\s+country\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bfrom\s+([A-Za-z ]+)\s+to\s+[A-Za-z ]+",
        ],
        text,
    )

    country_to = _first_text(
        [
            r"\bcountry_to\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bdestination\s+country\s*(?:is|=|:)\s*([A-Za-z ]+)",
            r"\bfrom\s+[A-Za-z ]+\s+to\s+([A-Za-z ]+)(?:\.|,|;|$)",
        ],
        text,
    )

    if country_from:
        route["origin"] = country_from
        route["origin_country"] = country_from
        route["country_from"] = country_from

    if country_to:
        route["destination"] = country_to
        route["destination_country"] = country_to
        route["country_to"] = country_to

    return route


def _extract_metadata(text: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    incoterm = _first_text(
        [
            r"\buse\s+(?:the\s+)?(?:incoterm\s+)?(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\s+incoterm\b",
            r"\bincoterm\s*(?:is|=|:)\s*(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b",
            r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\s+incoterm\b",
        ],
        text,
    )
    if incoterm:
        metadata["incoterm"] = incoterm.upper()
        metadata["trade_term"] = incoterm.upper()

    freight_quote = _first_number(
        [
            r"\bfreight\s+quote\s*(?:is|=|:)\s*[$]?([0-9,.]+)\s*(?:USD|dollars?)?\b",
        ],
        text,
    )
    if freight_quote is not None:
        metadata["freight_quote_usd"] = freight_quote

    insurance_premium = _first_number(
        [
            r"\binsurance\s+premium\s*(?:is|=|:)\s*[$]?([0-9,.]+)\s*(?:USD|dollars?)?\b",
        ],
        text,
    )
    if insurance_premium is not None:
        metadata["insurance_premium_usd"] = insurance_premium

    budget = _first_number(
        [
            r"\bbudget\s*(?:is|=|:)\s*[$]?([0-9,.]+)\s*(?:USD|dollars?)?\b",
        ],
        text,
    )
    if budget is not None:
        metadata["budget_usd"] = budget

    duty_rate = _first_number(
        [
            r"\bduty\s+rate\s*(?:is|=|:)\s*([0-9,.]+)\s*(?:%|percent|per\s+cent)\b",
        ],
        text,
    )
    if duty_rate is not None:
        metadata["duty_rate_percent"] = duty_rate

    import_tax_rate = _first_number(
        [
            r"\bimport\s+tax\s+rate\s*(?:is|=|:)\s*([0-9,.]+)\s*(?:%|percent|per\s+cent)\b",
            r"\btax\s+rate\s*(?:is|=|:)\s*([0-9,.]+)\s*(?:%|percent|per\s+cent)\b",
        ],
        text,
    )
    if import_tax_rate is not None:
        metadata["import_tax_rate_percent"] = import_tax_rate

    metadata.update(_extract_route(text))
    return metadata


def _remove_metadata_phrases(text: str) -> str:
    cleaned = text

    for pattern in _FIELD_REMOVAL_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    return cleaned


def _looks_like_metadata_chunk(chunk: str) -> bool:
    lowered = chunk.lower().strip(" .,:;")

    metadata_markers = [
        "freight quote",
        "insurance premium",
        "duty rate",
        "import tax rate",
        "tax rate",
        "incoterm",
        "budget",
    ]

    return any(marker in lowered for marker in metadata_markers)


def parse_shipment_text(text: str) -> dict[str, Any]:
    """
    Parses simple shipment text into item dictionaries and optional shipment
    metadata.

    Examples:
    - "10 cubic meters of tiles, 50 TVs, 5 scooters"
    - "estimate freight and find supplier for 100 ceramic tiles from India to USA.
       Use CIF incoterm. Freight quote is 1200 USD. Duty rate is 5 percent."
    """
    metadata = _extract_metadata(text)
    item_text = _remove_metadata_phrases(text)

    chunks = [
        chunk.strip()
        for chunk in _SPLIT_PATTERN.split(item_text)
        if chunk.strip()
    ]

    items: list[dict[str, Any]] = []
    issues: list[str] = []

    for chunk in chunks:
        if _looks_like_metadata_chunk(chunk):
            continue

        cbm_match = _CBM_PATTERN.match(chunk)

        if cbm_match:
            item_name = _clean_item_name(cbm_match.group("name"))
            if not item_name or item_name.lower() in _RATE_ONLY_NAMES:
                continue

            items.append(
                {
                    "name": item_name,
                    "quantity": 1,
                    "total_cbm": float(cbm_match.group("cbm")),
                    "volume_unit": cbm_match.group("unit"),
                }
            )
            continue

        quantity_match = _QUANTITY_PATTERN.match(chunk)

        if quantity_match:
            item_name = _clean_item_name(quantity_match.group("name"))
            if not item_name or item_name.lower() in _RATE_ONLY_NAMES:
                continue

            items.append(
                {
                    "name": item_name,
                    "quantity": int(quantity_match.group("quantity")),
                }
            )
            continue

        # Ignore connector/action fragments common in natural language prompts.
        lowered = chunk.lower().strip(" .,:;")
        if lowered in {"estimate freight", "find supplier", "find suppliers", "source supplier"}:
            continue

        issues.append(
            f"Could not parse item phrase: '{chunk}'. Use a pattern like '50 TVs' or '10 CBM of tiles'."
        )

    return {
        "items": items,
        "issues": issues,
        **metadata,
    }
