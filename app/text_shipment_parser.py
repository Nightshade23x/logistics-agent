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




_COUNTRY_CANONICAL_NAMES = {
    "usa": "USA",
    "u s a": "USA",
    "us": "USA",
    "u s": "USA",
    "america": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "india": "India",
    "germany": "Germany",
    "uk": "UK",
    "u k": "UK",
    "united kingdom": "UK",
    "england": "UK",
    "china": "China",
    "turkey": "Turkey",
    "turkiye": "Turkey",
    "uae": "UAE",
    "u a e": "UAE",
    "united arab emirates": "UAE",
    "iran": "Iran",
    "zambia": "Zambia",
    "finland": "Finland",
    "spain": "Spain",
    "portugal": "Portugal",
    "france": "France",
    "italy": "Italy",
    "netherlands": "Netherlands",
    "canada": "Canada",
    "mexico": "Mexico",
    "japan": "Japan",
    "south korea": "South Korea",
    "korea": "South Korea",
    "singapore": "Singapore",
    "australia": "Australia",
}

_ROUTE_STOP_WORDS = (
    "glass", "bottle", "bottles", "fragile", "hazardous", "battery", "batteries",
    "scooter", "scooters", "tv", "tvs", "television", "televisions",
    "ceramic", "tile", "tiles", "pillow", "pillows", "mattress", "mattresses",
    "use", "using", "with", "under", "freight", "insurance", "duty", "tax",
    "import", "budget", "quote", "rate", "incoterm", "fob", "cif", "exw",
    "dap", "ddp", "fca", "cfr", "and", "but",
)


def _route_normalized_text(value: str) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_route_country(value: str | None) -> str | None:
    """Return a clean country name from a noisy route fragment.

    This protects cases like:
    "USA Glass bottles are fragile Use FOB" -> "USA"
    """
    if not value:
        return None

    normalized = _route_normalized_text(value)

    if not normalized:
        return None

    # Prefer known country aliases at the start of the route fragment.
    for alias in sorted(_COUNTRY_CANONICAL_NAMES, key=len, reverse=True):
        if normalized == alias or normalized.startswith(alias + " "):
            return _COUNTRY_CANONICAL_NAMES[alias]

    # If the known country appears after small filler words, still recover it.
    for alias in sorted(_COUNTRY_CANONICAL_NAMES, key=len, reverse=True):
        pattern = rf"(?:^|\b)(?:country\s+)?{re.escape(alias)}(?:\b|$)"
        if re.search(pattern, normalized):
            return _COUNTRY_CANONICAL_NAMES[alias]

    # Generic fallback: stop before obvious cargo/metadata words.
    stop_pattern = r"\b(?:" + "|".join(re.escape(word) for word in _ROUTE_STOP_WORDS) + r")\b"
    cleaned = re.split(stop_pattern, normalized, maxsplit=1)[0].strip()

    if not cleaned:
        return None

    # Keep short country-like phrases only.
    words = cleaned.split()
    if len(words) > 4:
        words = words[:4]

    return " ".join(word.capitalize() for word in words) if words else None


def _extract_route_pair_from_text(text: str | None) -> dict[str, str | None]:
    """Extract origin/destination countries from free text with cleanup."""
    raw = text or ""
    route: dict[str, str | None] = {"country_from": None, "country_to": None}

    explicit_patterns = [
        (
            r"\b(?:origin|origin_country|country_from)\s*(?:is|=|:)\s*([A-Za-z .]+?)(?=,|;|\.|\b(?:destination|destination_country|country_to)\b|$)",
            "country_from",
        ),
        (
            r"\b(?:destination|destination_country|country_to)\s*(?:is|=|:)\s*([A-Za-z .]+?)(?=,|;|\.|\b(?:origin|origin_country|country_from)\b|$)",
            "country_to",
        ),
    ]

    for pattern, key in explicit_patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            route[key] = _clean_route_country(match.group(1))

    route_match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?=\.|,|;|\buse\b|\busing\b|\bwith\b|\bunder\b|\bbudget\b|\bfreight\b|\binsurance\b|\bduty\b|\bimport\s+tax\b|\btax\b|$)",
        raw,
        flags=re.IGNORECASE,
    )

    if route_match:
        route["country_from"] = route["country_from"] or _clean_route_country(route_match.group(1))
        route["country_to"] = route["country_to"] or _clean_route_country(route_match.group(2))

    return route


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
    extracted = _extract_route_pair_from_text(text)

    country_from = extracted.get("country_from")
    country_to = extracted.get("country_to")

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




def _extract_total_cargo_totals(text: str) -> dict[str, float]:
    """Extract aggregate shipment totals such as 'Total cargo is 10 CBM and 1200 kg'."""
    raw = text or ""
    totals: dict[str, float] = {}

    cbm_match = re.search(
        r"\b(?:total\s+)?(?:cargo|shipment|load)\s*(?:is|=|:)?\s*"
        r"(?P<cbm>\d+(?:\.\d+)?)\s*(?:cbm|m3|cubic\s+meters?)\b",
        raw,
        flags=re.IGNORECASE,
    )
    if cbm_match:
        totals["total_cbm"] = float(cbm_match.group("cbm"))

    weight_match = re.search(
        r"\b(?:total\s+)?(?:cargo|shipment|load).*?"
        r"(?P<weight>\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)\b",
        raw,
        flags=re.IGNORECASE,
    )
    if weight_match:
        totals["total_weight_kg"] = float(weight_match.group("weight"))

    return totals


def _remove_total_cargo_phrase(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(
        r"\b(?:total\s+)?(?:cargo|shipment|load)\s*(?:is|=|:)?\s*"
        r"\d+(?:\.\d+)?\s*(?:cbm|m3|cubic\s+meters?)"
        r"(?:\s*(?:and|,)\s*\d+(?:\.\d+)?\s*(?:kg|kgs|kilograms?))?",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:total\s+)?(?:cargo|shipment|load)\s*(?:weight\s*)?(?:is|=|:)?\s*"
        r"\d+(?:\.\d+)?\s*(?:kg|kgs|kilograms?)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


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

    route_pair = _extract_route_pair_from_text(raw_text)
    origin = route_pair.get("country_from")
    destination = route_pair.get("country_to")

    if origin:
        for key in ["country_from", "origin", "origin_country"]:
            metadata[key] = origin

    if destination:
        for key in ["country_to", "destination", "destination_country", "target_market"]:
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

    aggregate_totals = _extract_total_cargo_totals(raw_text)

    try:
        item_text = _remove_metadata_phrases(raw_text)
    except Exception:
        item_text = raw_text

    item_text = _remove_total_cargo_phrase(item_text)

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
        if re.fullmatch(r"(?:and\s+)?\d+(?:\.\d+)?\s*(?:kg|kgs|kilograms?|cbm|m3|cubic\s+meters?)", cleaned, flags=re.IGNORECASE):
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

    if items and aggregate_totals:
        primary_item = items[0]
        quantity_value = primary_item.get("quantity") or 1
        try:
            quantity_number = float(quantity_value)
        except Exception:
            quantity_number = 1.0

        if aggregate_totals.get("total_cbm") is not None:
            primary_item["total_cbm"] = aggregate_totals["total_cbm"]
            if quantity_number:
                primary_item["unit_cbm"] = round(aggregate_totals["total_cbm"] / quantity_number, 6)

        if aggregate_totals.get("total_weight_kg") is not None:
            primary_item["total_weight_kg"] = aggregate_totals["total_weight_kg"]
            if quantity_number:
                primary_item["unit_weight_kg"] = round(aggregate_totals["total_weight_kg"] / quantity_number, 6)

        note = "Aggregate shipment totals were provided in the user text and applied to this cargo line."
        if primary_item.get("notes"):
            primary_item["notes"] = str(primary_item["notes"]) + " " + note
        else:
            primary_item["notes"] = note

    result: dict[str, Any] = {"items": items, "issues": []}
    result.update(metadata)
    result.update(aggregate_totals)

    if not items:
        result["issues"].append("No requested items were provided.")

    return result


# Container-of-cargo short text parser support v1.
# Handles compact prompts such as:
# "20ft container of hazardous chemicals, destination Germany"
# This belongs in the parser, not user_agent routing.
try:
    _parse_shipment_text_before_container_of_cargo_v1 = parse_shipment_text

    def _container_v1_clean_country(value: str | None) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None

        aliases = {
            "usa": "USA",
            "us": "USA",
            "u.s.": "USA",
            "u.s.a.": "USA",
            "united states": "USA",
            "united states of america": "USA",
            "uk": "UK",
            "united kingdom": "UK",
            "uae": "UAE",
            "turkiye": "Turkey",
        }

        key = raw.lower()
        return aliases.get(key, raw[:1].upper() + raw[1:])

    def _container_v1_extract_destination(text: str | None) -> str | None:
        raw = str(text or "")

        country_group = (
            r"USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|"
            r"India|Germany|UK|United Kingdom|China|Turkey|Turkiye|UAE|Iran|"
            r"Zambia|Finland|Spain|Portugal|France|Italy|Canada|Mexico|Japan|"
            r"Singapore|Australia|Netherlands|Belgium|Sweden|Norway|Denmark"
        )

        patterns = [
            rf"\b(?:destination|dest|destination_country|country_to)\s*(?:is|=|:)?\s*({country_group})\b",
            rf"\bto\s+({country_group})\b",
            rf"\binto\s+({country_group})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match:
                return _container_v1_clean_country(match.group(1))

        return None

    def _container_v1_extract_origin(text: str | None) -> str | None:
        raw = str(text or "")

        country_group = (
            r"USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|"
            r"India|Germany|UK|United Kingdom|China|Turkey|Turkiye|UAE|Iran|"
            r"Zambia|Finland|Spain|Portugal|France|Italy|Canada|Mexico|Japan|"
            r"Singapore|Australia|Netherlands|Belgium|Sweden|Norway|Denmark"
        )

        match = re.search(rf"\bfrom\s+({country_group})\b", raw, flags=re.IGNORECASE)
        if match:
            return _container_v1_clean_country(match.group(1))

        return None

    def _container_v1_requested_container(text: str | None) -> str | None:
        raw = str(text or "")
        match = re.search(r"\b(20|40)\s*ft\b", raw, flags=re.IGNORECASE)
        if match:
            return f"{match.group(1)}ft Standard Container"
        if re.search(r"\bcontainer\b", raw, flags=re.IGNORECASE):
            return "20ft Standard Container"
        return None

    def _container_v1_extract_cargo_name(text: str | None) -> str | None:
        raw = str(text or "")

        patterns = [
            r"\b(?:20|40)\s*ft\s+container\s+of\s+(.+?)(?=,|;|\.|\bdestination\b|\bto\b|\bfrom\b|$)",
            r"\bcontainer\s+of\s+(.+?)(?=,|;|\.|\bdestination\b|\bto\b|\bfrom\b|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r"\s+", " ", name).strip(" ,.;:")
                if name:
                    return name.lower()

        return None

    def _container_v1_is_hazardous(text: str | None, cargo_name: str | None) -> bool:
        lowered = (str(text or "") + " " + str(cargo_name or "")).lower()
        return any(
            token in lowered
            for token in [
                "hazardous",
                "dangerous goods",
                "chemical",
                "chemicals",
                "battery",
                "batteries",
                "radioactive",
                "flammable",
                "corrosive",
            ]
        )

    def _container_v1_build_item(text: str | None) -> dict | None:
        cargo_name = _container_v1_extract_cargo_name(text)

        if not cargo_name:
            return None

        hazardous = _container_v1_is_hazardous(text, cargo_name)

        category_tags = ["general_cargo"]
        notes = "Container-of-cargo item extracted from compact free-text prompt."

        if hazardous:
            category_tags = ["hazardous", "chemical", "dangerous_goods", "non_stackable"]
            notes = (
                "Hazardous cargo; confirm UN number, hazard class, packing group, "
                "SDS/MSDS, packaging, quantity, and carrier acceptance."
            )

        return {
            "item_name": cargo_name,
            "quantity": 1,
            "dimensions_m": {
                "length": 1.2,
                "width": 1.0,
                "height": 1.0,
            },
            "unit_cbm": 1.2,
            "total_cbm": 1.2,
            "unit_weight_kg": 1000 if hazardous else 100,
            "total_weight_kg": 1000 if hazardous else 100,
            "stackable": False if hazardous else True,
            "hazardous": hazardous,
            "category_tags": category_tags,
            "notes": notes,
        }

    def parse_shipment_text(text: str):
        result = _parse_shipment_text_before_container_of_cargo_v1(text)

        if not isinstance(result, dict):
            return result

        raw = str(text or "")

        destination = _container_v1_extract_destination(raw)
        origin = _container_v1_extract_origin(raw)
        requested_container = _container_v1_requested_container(raw)
        fallback_item = _container_v1_build_item(raw)

        if destination:
            for key in ["destination", "destination_country", "country_to", "target_market"]:
                result[key] = destination

        if origin:
            for key in ["origin", "origin_country", "country_from"]:
                result[key] = origin

        if requested_container:
            result["requested_container"] = requested_container
            result["container_type"] = requested_container
            result["recommended_container"] = requested_container

        items = result.get("items")
        if not isinstance(items, list):
            items = []

        if fallback_item and not items:
            items.append(fallback_item)
            result["items"] = items

            result["total_cbm"] = fallback_item["total_cbm"]
            result["total_weight_kg"] = fallback_item["total_weight_kg"]

            if fallback_item.get("hazardous"):
                result.setdefault("issues", [])
                if isinstance(result["issues"], list):
                    result["issues"].append(
                        "Hazardous cargo requires DG classification, SDS/MSDS, packaging details, and carrier acceptance."
                    )

        return result

except Exception:
    pass

# JSON regression fixes v10: explicit shipment properties
#
# Explicit information in the prompt must override catalogue defaults.
try:
    _parse_shipment_text_before_json_regression_v10 = parse_shipment_text

    def _json_v10_float(value):
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return None

    def _json_v10_clean_item_name(value):
        name = str(value or "")

        name = re.sub(
            r"\s+\bweighing\s+[0-9][0-9,.]*\s*"
            r"(?:kg|kgs|kilograms?|lb|lbs|pounds?)\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(
            r"\s+\bfrom\s+.+$",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(
            r"\s+\b(?:under|using|use)\s+(?:the\s+)?"
            r"(?:EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b.*$",
            "",
            name,
            flags=re.IGNORECASE,
        )

        return re.sub(r"\s+", " ", name).strip(" ,.;:-")

    def _json_v10_explicit_weight(text):
        match = re.search(
            r"\bweighing\s+([0-9][0-9,.]*)\s*"
            r"(kg|kgs|kilograms?|lb|lbs|pounds?)\b",
            str(text or ""),
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        value = _json_v10_float(match.group(1))

        if value is None:
            return None

        unit = str(match.group(2)).lower()

        if unit in {"lb", "lbs", "pound", "pounds"}:
            value *= 0.45359237

        return round(value, 6)

    def _json_v10_explicit_cbm(text):
        match = re.search(
            r"\b([0-9][0-9,.]*)\s*"
            r"(?:cbm|m3|m\^3|cubic\s+meters?|cubic\s+metres?)\b",
            str(text or ""),
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return _json_v10_float(match.group(1))

    def parse_shipment_text(text: str):
        result = _parse_shipment_text_before_json_regression_v10(text)

        if not isinstance(result, dict):
            return result

        raw = str(text or "")
        lowered = raw.lower()

        weight = _json_v10_explicit_weight(raw)
        cbm = _json_v10_explicit_cbm(raw)

        items = result.get("items")

        if not isinstance(items, list):
            items = []
            result["items"] = items

        for item in items:
            if not isinstance(item, dict):
                continue

            item["name"] = _json_v10_clean_item_name(
                item.get("name")
                or item.get("item_name")
                or item.get("product_name")
                or "cargo"
            )

            quantity = item.get("quantity") or 1

            try:
                quantity_number = float(quantity)
            except Exception:
                quantity_number = 1.0

            if len(items) == 1 and weight is not None:
                item["total_weight_kg"] = weight
                item["unit_weight_kg"] = round(
                    weight / quantity_number,
                    6,
                )
                item["weight_kg"] = round(
                    weight / quantity_number,
                    6,
                )

            if len(items) == 1 and cbm is not None:
                item["total_cbm"] = cbm
                item["unit_cbm"] = round(
                    cbm / quantity_number,
                    6,
                )
                item["aggregate_volume_only"] = True
                item["dimensions_are_aggregate"] = True

            if (
                "non-stackable" in lowered
                or "non stackable" in lowered
                or "do not stack" in lowered
            ):
                item["stackable"] = False

            if any(
                token in lowered
                for token in [
                    "hazardous",
                    "dangerous goods",
                    "lithium battery",
                    "lithium batteries",
                    "radioactive",
                ]
            ):
                item["hazardous"] = True

        if weight is not None:
            result["total_weight_kg"] = weight

        if cbm is not None:
            result["total_cbm"] = cbm

        return result

except Exception:
    pass

# MULTI_ITEM_EXPLICIT_CLAUSES_V11
#
# Parse two or more complete item clauses at the parser boundary, for example:
#
#   10 CBM ceramic tiles weighing 1200 kg
#   and 4 CBM pillows weighing 350 kg
#
# Earlier wrappers correctly handled a single explicit CBM/weight pair, but
# intentionally read only the first match. This final parser wrapper preserves
# all complete item-level pairs and makes their sums authoritative before the
# Logistics Agent or backend response normalizers run.

_parse_shipment_text_before_multi_item_explicit_v11 = parse_shipment_text


def _multi_item_v11_number(value):
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _multi_item_v11_round(value):
    number = _multi_item_v11_number(value)

    if number is None:
        return None

    rounded = round(number, 6)

    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))

    return rounded


def _multi_item_v11_normalized_name(value):
    import re as _re

    text = str(value or "").strip().lower()
    text = _re.sub(r"[^a-z0-9]+", " ", text)
    return _re.sub(r"\s+", " ", text).strip()


def _multi_item_v11_clean_name(value):
    import re as _re

    name = str(value or "").strip(" ,.;:-")

    name = _re.sub(
        r"^(?:and|plus)\s+",
        "",
        name,
        flags=_re.IGNORECASE,
    )

    name = _re.sub(
        r"\s+\bfrom\s+.+$",
        "",
        name,
        flags=_re.IGNORECASE,
    )

    name = _re.sub(
        r"\s+\bto\s+.+$",
        "",
        name,
        flags=_re.IGNORECASE,
    )

    return _re.sub(r"\s+", " ", name).strip(" ,.;:-")


def _multi_item_v11_explicit_items(text):
    import re as _re

    raw = str(text or "")

    volume_unit = (
        r"(?:CBM|m\s*3|m³|cubic\s+met(?:er|re)s?)"
    )

    pattern = _re.compile(
        r"(?P<cbm>[0-9][0-9,]*(?:\.[0-9]+)?)"
        r"\s*" + volume_unit +
        r"\s+"
        r"(?:of\s+)?"
        r"(?P<name>.*?)"
        r"\s+weigh(?:ing|s)?\s+"
        r"(?P<weight>[0-9][0-9,]*(?:\.[0-9]+)?)"
        r"\s*(?P<weight_unit>kg|kgs|kilograms?|lb|lbs|pounds?)\b"
        r"(?=\s*(?:"
        r"(?:,\s*(?:and\s+)?|(?:and|plus|&)\s+)?"
        r"[0-9][0-9,]*(?:\.[0-9]+)?\s*" + volume_unit + r"\b"
        r"|\s+from\b"
        r"|\s+to\b"
        r"|[.;]"
        r"|$"
        r"))",
        flags=_re.IGNORECASE,
    )

    items = []

    for match in pattern.finditer(raw):
        cbm = _multi_item_v11_number(match.group("cbm"))
        weight = _multi_item_v11_number(match.group("weight"))
        name = _multi_item_v11_clean_name(match.group("name"))
        unit = str(match.group("weight_unit") or "").lower()

        if cbm is None or cbm <= 0:
            continue

        if weight is None or weight <= 0:
            continue

        if not name:
            continue

        if unit in {"lb", "lbs", "pound", "pounds"}:
            weight *= 0.45359237

        items.append(
            {
                "name": name,
                "item_name": name,
                "quantity": 1,
                "total_cbm": _multi_item_v11_round(cbm),
                "unit_cbm": _multi_item_v11_round(cbm),
                "total_weight_kg": _multi_item_v11_round(weight),
                "unit_weight_kg": _multi_item_v11_round(weight),
                "aggregate_volume_only": True,
                "dimensions_are_aggregate": True,
                "display_dimensions_estimated": True,
                "weight_estimated": False,
                "weight_source": "explicit_user_item_weight",
                "cbm_source": "explicit_user_item_cbm",
            }
        )

    return items if len(items) >= 2 else []


def _multi_item_v11_best_existing_item(parsed_name, existing_items):
    target = _multi_item_v11_normalized_name(parsed_name)

    if not target:
        return {}

    for item in existing_items:
        if not isinstance(item, dict):
            continue

        candidate = _multi_item_v11_normalized_name(
            item.get("name")
            or item.get("item_name")
            or item.get("product_name")
        )

        if candidate == target:
            return item

    for item in existing_items:
        if not isinstance(item, dict):
            continue

        candidate = _multi_item_v11_normalized_name(
            item.get("name")
            or item.get("item_name")
            or item.get("product_name")
        )

        if candidate and (
            candidate in target
            or target in candidate
        ):
            return item

    return {}


def _multi_item_v11_merge_properties(parsed_items, existing_items):
    safe_keys = (
        "stackable",
        "hazardous",
        "fragile",
        "non_stackable",
        "unload_priority",
        "category_tags",
        "notes",
        "handling_requirements",
        "special_handling",
    )

    merged_items = []

    for parsed in parsed_items:
        existing = _multi_item_v11_best_existing_item(
            parsed.get("item_name"),
            existing_items,
        )

        merged = {}

        for key in safe_keys:
            if key in existing:
                merged[key] = existing[key]

        merged.update(parsed)

        if not isinstance(merged.get("category_tags"), list):
            merged["category_tags"] = ["general_cargo"]

        merged_items.append(merged)

    return merged_items


def parse_shipment_text(text: str):
    result = _parse_shipment_text_before_multi_item_explicit_v11(text)

    if not isinstance(result, dict):
        return result

    parsed_items = _multi_item_v11_explicit_items(text)

    if len(parsed_items) < 2:
        return result

    existing_items = result.get("items")

    if not isinstance(existing_items, list):
        existing_items = []

    canonical_items = _multi_item_v11_merge_properties(
        parsed_items,
        existing_items,
    )

    total_cbm = sum(
        float(item["total_cbm"])
        for item in canonical_items
    )

    total_weight = sum(
        float(item["total_weight_kg"])
        for item in canonical_items
    )

    result["items"] = canonical_items
    result["total_cbm"] = _multi_item_v11_round(total_cbm)
    result["total_weight_kg"] = _multi_item_v11_round(total_weight)

    issues = result.get("issues")

    if isinstance(issues, list):
        stale_fragments = (
            "no requested items",
            "no shipment items",
            "which products",
            "exact item list",
        )

        result["issues"] = [
            issue
            for issue in issues
            if not any(
                fragment in str(issue or "").lower()
                for fragment in stale_fragments
            )
        ]

    return result

# DIRECT_VOLUME_UNIT_RESCUE_V12
#
# Preserve direct non-CBM volume inputs such as:
#
#   10 cubic feet of tiles
#
# The item resolver owns unit conversion. The parser therefore keeps the raw
# item volume plus its source unit, while exposing a canonical top-level CBM
# total for downstream summaries.

_parse_shipment_text_before_direct_volume_unit_v12 = parse_shipment_text


def _direct_volume_v12_number(value):
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _direct_volume_v12_extract(text):
    import re as _re

    raw = str(text or "").strip()

    pattern = _re.compile(
        r"^\s*"
        r"(?:(?:estimate\s+freight\s+for|ship|send|export|import)\s+)?"
        r"(?P<volume>[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
        r"(?P<unit>"
        r"cbm|m3|m\^3|m³|"
        r"cubic\s+meters?|cubic\s+metres?|"
        r"ft3|ft\^3|ft³|cubic\s+feet|cubic\s+foot"
        r")"
        r"\s+(?:of\s+)?"
        r"(?P<name>.+?)"
        r"\s*[.;]?\s*$",
        flags=_re.IGNORECASE,
    )

    match = pattern.match(raw)

    if not match:
        return None

    volume = _direct_volume_v12_number(
        match.group("volume")
    )

    if volume is None or volume <= 0:
        return None

    unit = _re.sub(
        r"\s+",
        " ",
        str(match.group("unit") or "").strip().lower(),
    )

    unit = unit.replace("ft³", "ft3").replace("m³", "m3")

    name = str(match.group("name") or "").strip(" ,.;:-")

    name = _re.sub(
        r"\s+\bfrom\b.+$",
        "",
        name,
        flags=_re.IGNORECASE,
    )

    name = _re.sub(
        r"\s+\bto\b.+$",
        "",
        name,
        flags=_re.IGNORECASE,
    )

    name = _re.sub(
        r"\s+",
        " ",
        name,
    ).strip(" ,.;:-")

    if not name:
        return None

    return {
        "name": name,
        "item_name": name,
        "quantity": 1,
        "cbm": volume,
        "total_cbm": volume,
        "volume_unit": unit,
        "cbm_unit": unit,
        "aggregate_volume_only": True,
        "dimensions_are_aggregate": True,
        "display_dimensions_estimated": True,
        "category_tags": ["general_cargo"],
    }


def parse_shipment_text(text: str):
    result = _parse_shipment_text_before_direct_volume_unit_v12(text)

    if not isinstance(result, dict):
        return result

    items = result.get("items")

    if isinstance(items, list) and items:
        return result

    direct_item = _direct_volume_v12_extract(text)

    if not direct_item:
        return result

    from app.unit_converter import convert_volume_to_cbm

    result["items"] = [direct_item]
    result["total_cbm"] = convert_volume_to_cbm(
        direct_item["total_cbm"],
        direct_item["volume_unit"],
    )

    issues = result.get("issues")

    if isinstance(issues, list):
        stale_fragments = (
            "no requested items",
            "no shipment items",
            "which products",
            "exact item list",
        )

        result["issues"] = [
            issue
            for issue in issues
            if not any(
                fragment in str(issue or "").lower()
                for fragment in stale_fragments
            )
        ]

    return result
