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
    """Parse natural-language shipment text into items plus metadata."""
    import re

    raw_text = text or ""

    try:
        metadata = _extract_metadata(raw_text)
    except Exception:
        metadata = {}

    route_match = re.search(
        r"\bfrom\s+([A-Za-z][A-Za-z\s]+?)\s+to\s+([A-Za-z][A-Za-z\s]+?)(?=\.|,|\s+use\b|\s+with\b|\s+the\b|\s+and\b|$)",
        raw_text,
        flags=re.IGNORECASE,
    )

    if route_match:
        origin = route_match.group(1).strip()
        destination = route_match.group(2).strip()
        for key in ["country_from", "origin", "origin_country"]:
            if not metadata.get(key):
                metadata[key] = origin
        for key in ["country_to", "destination", "destination_country", "target_market"]:
            if not metadata.get(key):
                metadata[key] = destination

    incoterm_match = re.search(r"\b(EXW|FOB|CIF|DAP|DDP|FCA|CFR)\b", raw_text, flags=re.IGNORECASE)
    if incoterm_match:
        metadata["incoterm"] = incoterm_match.group(1).upper()
        metadata["trade_term"] = incoterm_match.group(1).upper()

    numeric_fields = {
        "freight_quote_usd": r"\bfreight(?:\s+quote)?\s+(?:is\s+)?(?P<value>\d+(?:\.\d+)?)\s*(?:usd|dollars?)?",
        "insurance_premium_usd": r"\binsurance(?:\s+premium)?\s+(?:is\s+)?(?P<value>\d+(?:\.\d+)?)\s*(?:usd|dollars?)?",
        "duty_rate_percent": r"\bduty(?:\s+rate)?\s+(?:is\s+)?(?P<value>\d+(?:\.\d+)?)\s*(?:percent|%)?",
        "import_tax_rate_percent": r"\bimport\s+tax(?:\s+rate)?\s+(?:is\s+)?(?P<value>\d+(?:\.\d+)?)\s*(?:percent|%)?",
    }

    for key, pattern in numeric_fields.items():
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if match:
            metadata[key] = float(match.group("value"))

    try:
        item_text = _remove_metadata_phrases(raw_text)
    except Exception:
        item_text = raw_text

    item_text = re.sub(
        r"\b(?:freight quote|freight|insurance premium|insurance|duty rate|duty|import tax rate|import tax|tax rate|budget|cost)\s+(?:is\s+)?\d+(?:\.\d+)?\s*(?:usd|dollars?|percent|%)?",
        " ",
        item_text,
        flags=re.IGNORECASE,
    )
    item_text = re.sub(r"\buse\s+(?:EXW|FOB|CIF|DAP|DDP|FCA|CFR)(?:\s+incoterm)?", " ", item_text, flags=re.IGNORECASE)

    leading_noise = [
        r"^i\s+want\s+to\s+ship\s+",
        r"^i\s+need\s+to\s+ship\s+",
        r"^please\s+ship\s+",
        r"^ship\s+",
        r"^shipping\s+plan\s+for\s+",
        r"^find\s+suppliers?\s+and\s+shipping\s+plan\s+for\s+",
        r"^find\s+suppliers?\s+for\s+",
        r"^find\s+supplier\s+for\s+",
        r"^estimate\s+freight\s+and\s+find\s+supplier\s+for\s+",
        r"^estimate\s+freight\s+for\s+",
        r"^source\s+",
        r"^procure\s+",
    ]

    trailing_noise = [
        r"\s+from\s+[A-Za-z][A-Za-z\s]+?\s+to\s+[A-Za-z][A-Za-z\s]+.*$",
        r"\s+use\s+(EXW|FOB|CIF|DAP|DDP|FCA|CFR).*$",
        r"\s+with\s+(EXW|FOB|CIF|DAP|DDP|FCA|CFR).*$",
        r"\s+are\s+fragile.*$",
        r"\s+is\s+fragile.*$",
        r"\s+have\s+batteries.*$",
        r"\s+has\s+batteries.*$",
        r"\s+with\s+batteries.*$",
    ]

    blocked_items = {
        "percent", "percentage", "usd", "eur", "gbp", "dollars", "dollar",
        "freight", "quote", "insurance", "premium", "duty", "rate", "tax", "budget", "cost",
    }

    def clean_name(value: str) -> str:
        name = (value or "").strip(" .,;:-").lower()

        for pattern in leading_noise:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()

        for pattern in trailing_noise:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()

        name = re.sub(r"\b(and|with|use)\s*$", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"\s+", " ", name).strip(" .,;:-")
        return name

    def flags_for(name: str) -> dict[str, Any]:
        lowered_text = raw_text.lower()
        lowered_name = name.lower()
        flags: dict[str, Any] = {}

        if any(marker in lowered_name for marker in ["tv", "television", "glass", "bottle", "bottles", "ceramic", "tile", "tiles"]):
            flags["fragile"] = True

        if ("scooter" in lowered_name or "electric" in lowered_name) and ("battery" in lowered_text or "batteries" in lowered_text):
            flags["hazardous"] = True
            flags["notes"] = "Battery-powered item; confirm lithium battery details, UN number, packing instruction, and carrier acceptance."

        if "radioactive" in lowered_text or "radioactive" in lowered_name:
            flags["hazardous"] = True
            flags["radioactive"] = True
            flags["notes"] = "Radioactive or regulated cargo; specialist compliance and carrier acceptance required."

        return flags

    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_item(name: str, quantity: Any, extra: dict[str, Any] | None = None) -> None:
        cleaned = clean_name(name)

        if not cleaned:
            return
        if cleaned in blocked_items:
            return
        if any(word in blocked_items for word in cleaned.split()):
            return
        if len(cleaned) > 80:
            return

        key = (str(quantity), cleaned)
        if key in seen:
            return

        seen.add(key)

        item = {"name": cleaned, "quantity": quantity}
        item.update(flags_for(cleaned))

        if extra:
            item.update(extra)

        items.append(item)

    volume_pattern = re.compile(
        r"\b(?P<volume>\d+(?:\.\d+)?)\s*(?:cbm|cubic\s+meters?|m3)\s+(?:of\s+)?(?P<name>[A-Za-z][A-Za-z0-9 /-]*?)(?=,|\.|\band\b|\bfrom\b|\bto\b|$)",
        flags=re.IGNORECASE,
    )

    volume_spans = []

    for match in volume_pattern.finditer(item_text):
        volume = float(match.group("volume"))
        add_item(
            match.group("name"),
            1,
            {
                "total_cbm": volume,
                "notes": f"Cargo volume was provided as {volume:g} CBM; unit quantity was not specified.",
            },
        )
        volume_spans.append(match.span())

    if volume_spans:
        chars = list(item_text)
        for start, end in volume_spans:
            for index in range(start, end):
                chars[index] = " "
        item_text = "".join(chars)

    list_text = re.sub(r"\s+\band\b\s+", ", ", item_text, flags=re.IGNORECASE)

    quantity_pattern = re.compile(
        r"\b(?P<quantity>\d+(?:\.\d+)?)\s+(?!percent\b|percentage\b|usd\b|eur\b|gbp\b|cbm\b|cubic\b|m3\b)(?P<name>[A-Za-z][A-Za-z0-9 /-]*?)(?=,|\.|\bfrom\b|\bto\b|$)",
        flags=re.IGNORECASE,
    )

    for match in quantity_pattern.finditer(list_text):
        value = float(match.group("quantity"))
        quantity = int(value) if value.is_integer() else value
        add_item(match.group("name"), quantity)

    if not items:
        maybe_match = re.search(r"\b(?:maybe|such as|including)\s+(.+?)(?:,?\s+but\b|\.|$)", raw_text, flags=re.IGNORECASE)
        if maybe_match:
            for candidate in re.split(r",|\band\b", maybe_match.group(1), flags=re.IGNORECASE):
                if clean_name(candidate):
                    add_item(candidate, 1, {"needs_quantity_confirmation": True})

    result: dict[str, Any] = {"items": items, "issues": []}
    result.update(metadata)

    if not items:
        result["issues"].append("No requested items were provided.")

    return result
