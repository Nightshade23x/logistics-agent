from __future__ import annotations

import functools
import re
from typing import Any, Callable


COST_FIELDS = (
    "freight_quote_usd",
    "insurance_premium_usd",
    "duty_rate_percent",
    "import_tax_rate_percent",
    "customs_brokerage_usd",
    "local_delivery_usd",
)


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _clean_number(value: Any) -> int | float | None:
    number = _to_float(value)
    if number is None:
        return None
    if abs(number - round(number)) < 0.000001:
        return int(round(number))
    return round(number, 4)


def _clean_place(value: Any) -> str:
    text = str(value or "").strip()
    text = re.split(
        r"\s+(?:using|with|under|for|and|but|including|include|freight|insurance|duty|tax|vat|customs|local|cargo|total)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = text.strip(" .,:;()[]{}")

    aliases = {
        "usa": "USA",
        "u.s.a": "USA",
        "u.s.": "USA",
        "us": "USA",
        "united states": "USA",
        "uk": "UK",
        "u.k.": "UK",
        "united kingdom": "UK",
        "uae": "UAE",
        "u.a.e": "UAE",
    }

    return aliases.get(text.lower(), text)


def extract_shopping_cost_route_fields(text: Any) -> dict[str, Any]:
    raw = str(text or "")
    result: dict[str, Any] = {}

    patterns: dict[str, list[str]] = {
        "freight_quote_usd": [
            r"\bfreight\s+quote\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
            r"\bfreight\s+cost\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
            r"\bfreight\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
        ],
        "insurance_premium_usd": [
            r"\binsurance\s+premium\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
            r"\binsurance\s+cost\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
            r"\binsurance\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
        ],
        "duty_rate_percent": [
            r"\bduty\s+rate\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent|per\s+cent)\b",
            r"\bimport\s+duty\s+rate\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent|per\s+cent)\b",
            r"\bimport\s+duty\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent|per\s+cent)\b",
            r"\bduty\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent|per\s+cent)\b",
        ],
        "import_tax_rate_percent": [
            r"\bimport\s+tax\s+rate\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent|\s+tax\s+rate\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)per\s+cent)\b",
            r"\bimport\s+tax\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent|per\s+cent)\b",
            r"\bvat\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent|per\s+cent)\b",
        ],
        "customs_brokerage_usd": [
            r"\bcustoms\s+brokerage\s*(?:fee|cost|charge)?\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
            r"\bbrokerage\s*(?:fee|cost|charge)?\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
            r"\bcustoms\s+clearance\s*(?:fee|cost|charge)?\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
        ],
        "local_delivery_usd": [
            r"\blocal\s+delivery\s*(?:fee|cost|charge)?\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
            r"\blast\s+mile\s*(?:fee|cost|charge)?\s*(?:is|of|:)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?)?\b",
        ],
    }

    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match:
                number = _clean_number(match.group(1))
                if number is not None:
                    result[field] = number
                    break

    from_to = re.search(
        r"\bfrom\s+([A-Z][A-Za-z .&-]{1,50}?)\s+to\s+([A-Z][A-Za-z .&-]{1,50}?)(?=\s+(?:using|with|under|for|and|but|including|include|freight|insurance|duty|tax|vat|customs|local)\b|[,.]|$)",
        raw,
        flags=re.IGNORECASE,
    )

    if from_to:
        origin = _clean_place(from_to.group(1))
        destination = _clean_place(from_to.group(2))
        result["origin"] = origin
        result["origin_country"] = origin
        result["destination"] = destination
        result["destination_country"] = destination
        return result

    destination_label = re.search(
        r"\bdestination\s*[:=-]?\s*([A-Z][A-Za-z .&-]{1,50})",
        raw,
        flags=re.IGNORECASE,
    )
    if destination_label:
        destination = _clean_place(destination_label.group(1))
        result["destination"] = destination
        result["destination_country"] = destination

    known_countries = (
        "USA|United States|US|Germany|Canada|Australia|UK|United Kingdom|UAE|India|China|Vietnam|Kenya|France|Japan|South Korea|Singapore|Netherlands|Spain|Portugal|Italy|Mexico|Brazil"
    )

    inline_to = re.search(r"\bto\s+(" + known_countries + r")\b", raw, flags=re.IGNORECASE)
    if inline_to and "destination_country" not in result:
        destination = _clean_place(inline_to.group(1))
        result["destination"] = destination
        result["destination_country"] = destination

    inline_from = re.search(r"\bfrom\s+(" + known_countries + r")\b", raw, flags=re.IGNORECASE)
    if inline_from:
        origin = _clean_place(inline_from.group(1))
        result["origin"] = origin
        result["origin_country"] = origin

    return result


def _missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _set_if_missing(target: dict[str, Any], key: str, value: Any) -> None:
    if _missing(target.get(key)):
        target[key] = value


def enrich_shopping_parse_result(result: Any, text: Any) -> Any:
    if not isinstance(result, dict):
        return result

    extracted = extract_shopping_cost_route_fields(text)
    if not extracted:
        return result

    for key, value in extracted.items():
        _set_if_missing(result, key, value)

    for nested_key in ("handoff_payload", "finance_inputs", "cost_inputs", "input_resolution", "shipment_input", "logistics_input", "shopping_request"):
        nested = result.get(nested_key)
        if not isinstance(nested, dict):
            nested = {}
            result[nested_key] = nested

        for key, value in extracted.items():
            if nested_key in ("finance_inputs", "cost_inputs") and key not in COST_FIELDS:
                continue
            _set_if_missing(nested, key, value)

    result["shopping_text_parser_enriched"] = True
    result["shopping_text_parser_extracted_fields"] = sorted(extracted.keys())

    return result


def _prompt_from_call(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    for value in args:
        if isinstance(value, str) and value.strip():
            return value

    for key in ("text", "prompt", "query", "message", "input_text", "user_message", "request_text"):
        value = kwargs.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return ""


def install_shopping_parser_final_wrappers(namespace: dict[str, Any]) -> None:
    if namespace.get("_shopping_parser_final_wrappers_installed"):
        return

    for name, value in list(namespace.items()):
        if name.startswith("_"):
            continue
        if "parse" not in name.lower():
            continue
        if not callable(value):
            continue
        if getattr(value, "_shopping_parser_final_wrapped", False):
            continue

        def make_wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                result = func(*args, **kwargs)
                text = _prompt_from_call(args, kwargs)
                return enrich_shopping_parse_result(result, text)

            wrapped._shopping_parser_final_wrapped = True
            return wrapped

        namespace[name] = make_wrapper(value)

    namespace["_shopping_parser_final_wrappers_installed"] = True


def enrich_backend_payload(payload: Any, prompt: Any = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = str(prompt or "")

    if not text.strip():
        for key in ("prompt", "input_text", "request_text", "query", "message", "user_message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                text = value
                break

    return enrich_shopping_parse_result(payload, text)
