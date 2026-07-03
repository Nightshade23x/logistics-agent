from __future__ import annotations

import re
from typing import Any


_SPLIT_PATTERN = re.compile(r"\s*(?:,|;|\band\b)\s*", re.IGNORECASE)

_CBM_PATTERN = re.compile(
    r"^(?P<cbm>\d+(?:\.\d+)?)\s*(?:cbm|cubic meters?|cubic metres?)\s+(?:of\s+)?(?P<name>.+)$",
    re.IGNORECASE,
)

_QUANTITY_PATTERN = re.compile(
    r"^(?P<quantity>\d+)\s+(?P<name>.+)$",
    re.IGNORECASE,
)


def _clean_item_name(name: str) -> str:
    return name.strip().strip(".").strip()


def parse_shipment_text(text: str) -> dict[str, Any]:
    """
    Parses simple shipment text into item dictionaries.

    Example:
    "10 cubic meters of tiles, 50 TVs, 5 scooters"
    """
    chunks = [
        chunk.strip()
        for chunk in _SPLIT_PATTERN.split(text)
        if chunk.strip()
    ]

    items: list[dict[str, Any]] = []
    issues: list[str] = []

    for chunk in chunks:
        cbm_match = _CBM_PATTERN.match(chunk)

        if cbm_match:
            items.append(
                {
                    "name": _clean_item_name(cbm_match.group("name")),
                    "quantity": 1,
                    "total_cbm": float(cbm_match.group("cbm")),
                }
            )
            continue

        quantity_match = _QUANTITY_PATTERN.match(chunk)

        if quantity_match:
            items.append(
                {
                    "name": _clean_item_name(quantity_match.group("name")),
                    "quantity": int(quantity_match.group("quantity")),
                }
            )
            continue

        issues.append(
            f"Could not parse item phrase: '{chunk}'. Use a pattern like '50 TVs' or '10 CBM of tiles'."
        )

    return {
        "items": items,
        "issues": issues,
    }
