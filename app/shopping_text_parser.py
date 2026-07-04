from __future__ import annotations

import re
from typing import Any


def _clean_value(value: str) -> str:
    cleaned = value.strip().strip(".:,;")

    if cleaned.upper() in {"USA", "UK", "UAE", "EU"}:
        return cleaned.upper()

    return cleaned.title()


def _clean_product_name(value: str) -> str:
    cleaned = value.strip().strip(".:,;")
    cleaned = re.sub(r"\b(units?|pieces?|pcs?)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split())

    uppercase_words = {"tv", "tvs", "usa", "uk", "uae", "eu"}

    words = []
    for word in cleaned.split():
        if word.lower() in uppercase_words:
            words.append("TVs" if word.lower() == "tvs" else ("TV" if word.lower() == "tv" else word.upper()))
        else:
            words.append(word.capitalize())

    return " ".join(words)


def _parse_number(value: str) -> float:
    return float(value.replace(",", "").strip())


def _parse_country_list(value: str) -> list[str]:
    value = value.replace("&", " and ")
    parts = re.split(r",|\band\b|/", value, flags=re.IGNORECASE)

    countries = []
    for part in parts:
        cleaned = _clean_value(part)
        if cleaned:
            countries.append(cleaned)

    return countries


def _extract_labeled_value(text: str, labels: list[str]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"^\s*(?:{label_pattern})\s*:\s*(.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    if not match:
        return None

    return match.group(1).strip()


def _extract_country_preference(text: str) -> list[str]:
    patterns = [
        r"\bprefer(?:red)?\s+suppliers?\s+(?:from|in)\s+(.+?)(?:\.|\n|$)",
        r"\bprefer(?:red)?\s+supplier\s+countries?\s*:\s*(.+?)(?:\.|\n|$)",
        r"\bsource\s+(?:from|in)\s+(.+?)(?:\.|\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _parse_country_list(match.group(1))

    return []


def _extract_excluded_countries(text: str) -> list[str]:
    patterns = [
        r"\bavoid\s+(.+?)(?:\.|\n|$)",
        r"\bexclude\s+suppliers?\s+(?:from|in)\s+(.+?)(?:\.|\n|$)",
        r"\bexcluded\s+supplier\s+countries?\s*:\s*(.+?)(?:\.|\n|$)",
        r"\bdo\s+not\s+use\s+suppliers?\s+(?:from|in)\s+(.+?)(?:\.|\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _parse_country_list(match.group(1))

    return []


def _extract_max_lead_time(text: str) -> int | None:
    patterns = [
        r"\bmax(?:imum)?\s+lead\s+time\s*(?:is|:)?\s*(\d+)",
        r"\blead\s+time\s+(?:under|below|less\s+than|maximum|max)\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def _extract_min_quality(text: str) -> float | None:
    patterns = [
        r"\bmin(?:imum)?\s+quality(?:\s+score)?\s*(?:is|:)?\s*(\d+(?:\.\d+)?)",
        r"\bquality(?:\s+score)?\s+(?:above|over|at\s+least)\s*(\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


def _extract_budget(text: str) -> float | None:
    patterns = [
        r"\bmax(?:imum)?\s+budget\s*(?:is|:)?\s*([\d,]+(?:\.\d+)?)",
        r"\bbudget\s*(?:is|:)?\s*([\d,]+(?:\.\d+)?)",
        r"\bunder\s+([\d,]+(?:\.\d+)?)\s*usd\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _parse_number(match.group(1))

    return None


def _parse_item_segment(segment: str) -> dict[str, Any] | None:
    match = re.search(
        r"(?P<quantity>\d+)\s+(?P<name>[A-Za-z][A-Za-z0-9\s\-]+)",
        segment,
    )

    if not match:
        return None

    quantity = int(match.group("quantity"))
    name = _clean_product_name(match.group("name"))

    ignored_names = {
        "days",
        "day",
        "usd",
        "dollars",
        "quality",
        "quality score",
        "lead time",
    }

    if not name or name.lower() in ignored_names:
        return None

    return {
        "name": name,
        "quantity": quantity,
    }


def _parse_item_phrase(phrase: str) -> list[dict[str, Any]]:
    items = []
    parts = re.split(r",|\band\b", phrase, flags=re.IGNORECASE)

    for part in parts:
        parsed = _parse_item_segment(part)
        if parsed:
            items.append(parsed)

    return items


def _extract_items_from_bullets(text: str) -> list[dict[str, Any]]:
    items = []

    for line in text.splitlines():
        cleaned = line.strip()

        if cleaned.startswith(("-", "*")):
            cleaned = cleaned[1:].strip()

        if re.match(r"^\d+\s+[A-Za-z]", cleaned):
            parsed = _parse_item_segment(cleaned)
            if parsed:
                items.append(parsed)

    return items


def _extract_items_from_sentences(text: str) -> list[dict[str, Any]]:
    items = []
    seen_phrases = set()

    patterns = [
        r"\bI\s+need\s+(.+?)(?:\.|\n|$)",
        r"\bneed\s+(.+?)(?:\.|\n|$)",
        r"\bwant\s+(?:to\s+buy\s+|to\s+source\s+)?(.+?)(?:\.|\n|$)",
        r"\bbuy\s+(.+?)(?:\.|\n|$)",
        r"\bsource\s+(.+?)(?:\.|\n|$)",
        r"\border\s+(.+?)(?:\.|\n|$)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            phrase = match.group(1).strip()
            phrase_key = " ".join(phrase.lower().split())

            if phrase_key in seen_phrases:
                continue

            seen_phrases.add(phrase_key)
            items.extend(_parse_item_phrase(phrase))

    return items


def _combine_duplicate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}

    for item in items:
        key = item["name"].lower()

        if key not in combined:
            combined[key] = dict(item)
        else:
            combined[key]["quantity"] += item["quantity"]

    return list(combined.values())


def parse_shopping_request_text(text: str) -> dict[str, Any]:
    request_id = _extract_labeled_value(text, ["Request ID", "Request"])
    customer = _extract_labeled_value(text, ["Customer", "Client"])
    destination = _extract_labeled_value(text, ["Destination", "Destination Country"])
    currency = _extract_labeled_value(text, ["Currency", "Preferred Currency"])

    items = []
    items.extend(_extract_items_from_bullets(text))
    items.extend(_extract_items_from_sentences(text))
    items = _combine_duplicate_items(items)

    preferences = {
        "preferred_supplier_countries": _extract_country_preference(text),
        "excluded_supplier_countries": _extract_excluded_countries(text),
        "max_lead_time_days": _extract_max_lead_time(text),
        "minimum_quality_score": _extract_min_quality(text),
        "max_budget_usd": _extract_budget(text),
    }

    return {
        "request_id": request_id or "SHOP-TEXT-REQUEST",
        "customer": customer or "Unknown Customer",
        "destination_country": _clean_value(destination) if destination else None,
        "preferred_currency": currency.upper() if currency else "USD",
        "preferences": preferences,
        "items": items,
        "input_type": "natural_language_text",
    }


def read_shopping_request_text(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as file:
        return parse_shopping_request_text(file.read())
