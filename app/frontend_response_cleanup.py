from __future__ import annotations

import re
from typing import Any


_BAD_ROUTE_PATTERNS = [
    (re.compile(r"\bUSA\s+Glass bottles are fragile Use FOB\b", re.IGNORECASE), "USA"),
    (re.compile(r"\bUSA\s+Give HS code duty FTA\b", re.IGNORECASE), "USA"),
    (re.compile(r"\bUSA\?\s+Tell me compliance risk logistics\b", re.IGNORECASE), "USA"),
    (
        re.compile(
            r"\bUSA(?:\?|\.|,)?\s+(?:Glass|Give|Tell|Use|The|They|compliance|risk|logistics|HS|code|duty|FTA)[^.,;]*",
            re.IGNORECASE,
        ),
        "USA",
    ),
    (
        re.compile(
            r"\bUnited States\s+(?:using|Use|They|The|Give|Tell)[^.,;]*",
            re.IGNORECASE,
        ),
        "USA",
    ),
]


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _extract_text(payload: Any, fallback: str | None = None) -> str:
    if fallback:
        return str(fallback)

    if isinstance(payload, dict):
        request_metadata = payload.get("request_metadata")
        if isinstance(request_metadata, dict) and request_metadata.get("input_source"):
            return str(request_metadata.get("input_source"))

        for key in ["input_source", "user_text", "request_text", "original_text", "prompt"]:
            if payload.get(key):
                return str(payload.get(key))

    return ""


def _clean_country(value: str | None) -> str | None:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z. ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    aliases = {
        "usa": "USA",
        "us": "USA",
        "u.s.": "USA",
        "u.s.a.": "USA",
        "united states": "USA",
        "united states of america": "USA",
        "india": "India",
        "china": "China",
        "turkey": "Turkey",
        "turkiye": "Turkey",
        "uk": "UK",
        "united kingdom": "UK",
        "uae": "UAE",
        "iran": "Iran",
        "germany": "Germany",
        "zambia": "Zambia",
        "finland": "Finland",
    }

    for alias in sorted(aliases, key=len, reverse=True):
        if text == alias or text.startswith(alias + " "):
            return aliases[alias]

    return None


def _extract_route(text: str) -> dict[str, str | None]:
    route = {"country_from": None, "country_to": None}

    match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?=\.|,|;|\?|\buse\b|\busing\b|\bwith\b|\bunder\b|\btell\b|\bgive\b|\bglass\b|\bthe\b|\bthey\b|$)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        route["country_from"] = _clean_country(match.group(1))
        route["country_to"] = _clean_country(match.group(2))

    if not route["country_to"]:
        match = re.search(
            r"\bto\s+(USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|India|China|Turkey|Turkiye|UK|United Kingdom|UAE|Iran|Germany|Zambia|Finland)\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            route["country_to"] = _clean_country(match.group(1))

    if not route["country_from"]:
        match = re.search(
            r"\bfrom\s+(USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|India|China|Turkey|Turkiye|UK|United Kingdom|UAE|Iran|Germany|Zambia|Finland)\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            route["country_from"] = _clean_country(match.group(1))

    return route


def _extract_trade_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    incoterms = "EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP"

    for pattern in [
        rf"\buse\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\busing\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\bwith\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\bunder\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\bincoterm\s*(?:is|=|:)?\s*({incoterms})\b",
    ]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            fields["incoterm"] = match.group(1).upper()
            fields["trade_term"] = match.group(1).upper()
            break

    cost_patterns = {
        "freight_quote_usd": r"\bfreight\s+quote\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
        "insurance_premium_usd": r"\binsurance\s*(?:premium|cost|quote)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
        "duty_rate_percent": r"\bduty\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
        "import_tax_rate_percent": r"\bimport\s+tax\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
    }

    for key, pattern in cost_patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _as_float(match.group(1))
            if value is not None:
                fields[key] = value

    return fields


def _extract_totals(text: str) -> dict[str, float]:
    totals: dict[str, float] = {}

    cbm_match = re.search(
        r"\b(?:total\s+)?(?:cargo|shipment|load)\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:cbm|m3|cubic\s+meters?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if cbm_match:
        value = _as_float(cbm_match.group(1))
        if value is not None:
            totals["total_cbm"] = value

    kg_match = re.search(
        r"\b(?:total\s+)?(?:cargo|shipment|load).*?([0-9][0-9,.]*)\s*(?:kg|kgs|kilograms?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if kg_match:
        value = _as_float(kg_match.group(1))
        if value is not None:
            totals["total_weight_kg"] = value

    return totals


def _clean_string(value: str, destination: str | None) -> str:
    result = value

    for pattern, replacement in _BAD_ROUTE_PATTERNS:
        result = pattern.sub(destination or replacement, result)

    return result


def _filter_missing_list(values: list[Any], trade_fields: dict[str, Any], destination: str | None) -> list[Any]:
    known = set(trade_fields.keys()) | {"trade_term"}

    cleaned: list[Any] = []

    for value in values:
        text = str(value).strip()
        lower = text.lower()

        if destination and lower == "destination country":
            continue

        if trade_fields.get("incoterm") and (
            "which incoterm" in lower
            or "incoterm is missing" in lower
            or "no incoterm" in lower
            or lower == "trade_terms needs more information."
        ):
            continue

        if text in known:
            continue

        if text.startswith("landed cost input: "):
            key = text.replace("landed cost input: ", "", 1)
            if key in known:
                continue

        cleaned.append(value)

    return cleaned


def _apply_totals(payload: dict[str, Any], totals: dict[str, float]) -> None:
    if not totals:
        return

    metrics = payload.setdefault("logistics_metrics", {})
    if isinstance(metrics, dict):
        metrics.update(totals)

    visualizer = payload.get("logistics_visualizer")
    if not isinstance(visualizer, dict):
        return

    container = visualizer.setdefault("container", {})
    if isinstance(container, dict):
        container.update(totals)

    cargo_mix = visualizer.get("cargo_mix")
    if isinstance(cargo_mix, list) and cargo_mix:
        first = cargo_mix[0]
        if isinstance(first, dict):
            quantity = first.get("quantity") or 1
            try:
                quantity = float(quantity)
            except Exception:
                quantity = 1.0

            if "total_cbm" in totals:
                first["total_cbm"] = totals["total_cbm"]
                if quantity:
                    first["unit_cbm"] = round(totals["total_cbm"] / quantity, 6)

            if "total_weight_kg" in totals:
                first["total_weight_kg"] = totals["total_weight_kg"]
                if quantity:
                    first["unit_weight_kg"] = round(totals["total_weight_kg"] / quantity, 6)


def cleanup_frontend_response(payload: Any, original_text: str | None = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = _extract_text(payload, original_text)
    route = _extract_route(text)
    origin = route.get("country_from")
    destination = route.get("country_to")
    trade_fields = _extract_trade_fields(text)
    totals = _extract_totals(text)

    def visit(obj: Any, path: str = "") -> Any:
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                value = obj[key]
                lower_key = str(key).lower()

                if path.endswith("request_metadata") and lower_key == "input_source":
                    continue

                if origin and lower_key in {"origin", "origin_country", "country_from"}:
                    obj[key] = origin
                    continue

                if destination and lower_key in {"destination", "destination_country", "country_to", "target_market"}:
                    obj[key] = destination
                    continue

                if lower_key in {"incoterm", "trade_term"} and trade_fields.get(lower_key):
                    obj[key] = trade_fields[lower_key]
                    continue

                obj[key] = visit(value, f"{path}.{key}" if path else str(key))

            known_inputs = obj.get("known_inputs")
            if isinstance(known_inputs, dict):
                if origin:
                    known_inputs["origin_country"] = origin
                if destination:
                    known_inputs["destination_country"] = destination
                known_inputs.update(trade_fields)

            for list_key in ["missing_cost_inputs", "missing_information", "missing_information_preview", "user_questions"]:
                if isinstance(obj.get(list_key), list):
                    obj[list_key] = _filter_missing_list(obj[list_key], trade_fields, destination)

            return obj

        if isinstance(obj, list):
            filtered = _filter_missing_list(obj, trade_fields, destination)
            return [visit(item, f"{path}[]") for item in filtered]

        if isinstance(obj, str):
            return _clean_string(obj, destination)

        return obj

    payload = visit(payload)

    if trade_fields:
        payload.setdefault("text_cost_inputs", {})
        if isinstance(payload["text_cost_inputs"], dict):
            payload["text_cost_inputs"].update(trade_fields)

    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict) and not visualizer.get("cargo_mix"):
        visualizer["status"] = "unavailable"

    _apply_totals(payload, totals)

    return payload
