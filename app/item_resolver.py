from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "item_catalog.json"


def _normalize_name(name: str) -> str:
    return name.lower().strip().replace("-", " ")


def load_item_catalog(catalog_path: Path | None = None) -> list[dict[str, Any]]:
    path = catalog_path or CATALOG_PATH

    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def find_catalog_match(item_name: str, catalog: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_item_name = _normalize_name(item_name)

    for catalog_item in catalog:
        possible_names = [catalog_item["canonical_name"], *catalog_item.get("aliases", [])]
        normalized_names = {_normalize_name(name) for name in possible_names}

        if normalized_item_name in normalized_names:
            return catalog_item

    return None


def _has_dimensions(raw_item: dict[str, Any]) -> bool:
    return all(
        key in raw_item and raw_item[key] not in {None, ""}
        for key in ["length_m", "width_m", "height_m"]
    )


def _merge_with_catalog(raw_item: dict[str, Any], catalog_item: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "name": raw_item.get("name", catalog_item["canonical_name"]),
        "quantity": raw_item["quantity"],
        "length_m": raw_item.get("length_m", catalog_item["length_m"]),
        "width_m": raw_item.get("width_m", catalog_item["width_m"]),
        "height_m": raw_item.get("height_m", catalog_item["height_m"]),
        "weight_kg": raw_item.get("weight_kg", catalog_item.get("weight_kg", 0.0)),
        "fragile": raw_item.get("fragile", catalog_item.get("fragile", False)),
        "perishable": raw_item.get("perishable", catalog_item.get("perishable", False)),
        "hazardous": raw_item.get("hazardous", catalog_item.get("hazardous", False)),
        "radioactive": raw_item.get("radioactive", catalog_item.get("radioactive", False)),
        "stackable": raw_item.get("stackable", catalog_item.get("stackable", True)),
        "unload_priority": raw_item.get("unload_priority", catalog_item.get("unload_priority", 3)),
    }

    return merged


def resolve_items(raw_items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Converts a simple item list into full cargo item data.

    If dimensions are already provided, the item is used directly.
    If dimensions are missing, the item catalog is used to estimate them.
    If no catalog match exists, the item is returned as unresolved.
    """
    catalog = load_item_catalog()
    resolved_items: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    issues: list[str] = []

    for raw_item in raw_items:
        item_name = raw_item.get("name", "Unknown item")

        if "quantity" not in raw_item:
            unresolved_items.append(raw_item)
            issues.append(f"{item_name}: missing quantity.")
            continue

        if _has_dimensions(raw_item):
            resolved_items.append(raw_item)
            continue

        catalog_match = find_catalog_match(item_name, catalog)

        if catalog_match is None:
            unresolved_items.append(raw_item)
            issues.append(
                f"{item_name}: missing dimensions and no catalog match found. "
                "Length, width, and height are required for CBM calculation."
            )
            continue

        resolved_items.append(_merge_with_catalog(raw_item, catalog_match))
        issues.append(
            f"{item_name}: dimensions and handling properties were estimated from the item catalog."
        )

    return {
        "resolved_items": resolved_items,
        "unresolved_items": unresolved_items,
        "issues": issues,
    }
