from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.unit_converter import convert_volume_to_cbm


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "item_catalog.json"
FUZZY_MATCH_THRESHOLD = 0.78


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().strip().replace("-", " ").split())


def _singularize(word: str) -> str:
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"

    if word.endswith("s") and len(word) > 3:
        return word[:-1]

    return word


def _normalized_tokens(name: str) -> set[str]:
    return {_singularize(token) for token in _normalize_name(name).split()}


def load_item_catalog(catalog_path: Path | None = None) -> list[dict[str, Any]]:
    path = catalog_path or CATALOG_PATH

    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _candidate_names(catalog_item: dict[str, Any]) -> list[str]:
    return [catalog_item["canonical_name"], *catalog_item.get("aliases", [])]


def _match_score(item_name: str, candidate_name: str) -> float:
    normalized_item = _normalize_name(item_name)
    normalized_candidate = _normalize_name(candidate_name)

    if normalized_item == normalized_candidate:
        return 1.0

    item_tokens = _normalized_tokens(normalized_item)
    candidate_tokens = _normalized_tokens(normalized_candidate)

    if item_tokens == candidate_tokens:
        return 0.98

    if normalized_candidate in normalized_item or normalized_item in normalized_candidate:
        return 0.92

    token_overlap = 0.0
    if item_tokens and candidate_tokens:
        token_overlap = len(item_tokens.intersection(candidate_tokens)) / len(
            item_tokens.union(candidate_tokens)
        )

    sequence_score = SequenceMatcher(
        None,
        normalized_item,
        normalized_candidate,
    ).ratio()

    return max(sequence_score, token_overlap)


def _find_catalog_match_with_score(
    item_name: str,
    catalog: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None, float]:
    best_item: dict[str, Any] | None = None
    best_name: str | None = None
    best_score = 0.0

    for catalog_item in catalog:
        for candidate_name in _candidate_names(catalog_item):
            score = _match_score(item_name, candidate_name)

            if score > best_score:
                best_item = catalog_item
                best_name = candidate_name
                best_score = score

    if best_score >= FUZZY_MATCH_THRESHOLD:
        return best_item, best_name, best_score

    return None, None, best_score


def find_catalog_match(item_name: str, catalog: list[dict[str, Any]]) -> dict[str, Any] | None:
    catalog_item, _, _ = _find_catalog_match_with_score(item_name, catalog)
    return catalog_item


def _has_dimensions(raw_item: dict[str, Any]) -> bool:
    return all(
        key in raw_item and raw_item[key] not in {None, ""}
        for key in ["length_m", "width_m", "height_m"]
    )


def _has_direct_cbm(raw_item: dict[str, Any]) -> bool:
    return raw_item.get("total_cbm") not in {None, ""} or raw_item.get("cbm") not in {None, ""}


def _merge_with_catalog(raw_item: dict[str, Any], catalog_item: dict[str, Any]) -> dict[str, Any]:
    return {
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


def _merge_direct_cbm(
    raw_item: dict[str, Any],
    catalog_item: dict[str, Any] | None,
) -> dict[str, Any]:
    quantity = int(raw_item.get("quantity", 1))
    raw_volume = float(raw_item.get("total_cbm", raw_item.get("cbm")))
    volume_unit = raw_item.get("volume_unit", raw_item.get("cbm_unit", "cbm"))
    total_cbm = convert_volume_to_cbm(raw_volume, volume_unit)
    unit_cbm = total_cbm / quantity

    base = catalog_item or {}

    return {
        "name": raw_item.get("name", base.get("canonical_name", "Unknown item")),
        "quantity": quantity,
        "length_m": unit_cbm,
        "width_m": 1.0,
        "height_m": 1.0,
        "weight_kg": raw_item.get("weight_kg", base.get("weight_kg", 0.0)),
        "fragile": raw_item.get("fragile", base.get("fragile", False)),
        "perishable": raw_item.get("perishable", base.get("perishable", False)),
        "hazardous": raw_item.get("hazardous", base.get("hazardous", False)),
        "radioactive": raw_item.get("radioactive", base.get("radioactive", False)),
        "stackable": raw_item.get("stackable", base.get("stackable", True)),
        "unload_priority": raw_item.get("unload_priority", base.get("unload_priority", 3)),
    }


def resolve_items(raw_items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Converts a simple item list into full cargo item data.

    Supported input styles:
    - Full dimensions: length_m, width_m, height_m
    - Catalog-based lookup: item name + quantity
    - Direct CBM: item name + total_cbm/cbm
    - Fuzzy catalog matching for close item names
    """
    catalog = load_item_catalog()
    resolved_items: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    issues: list[str] = []

    for raw_item in raw_items:
        item_name = raw_item.get("name", "Unknown item")

        catalog_match, matched_name, score = _find_catalog_match_with_score(item_name, catalog)

        if _has_direct_cbm(raw_item):
            resolved_items.append(_merge_direct_cbm(raw_item, catalog_match))
            issues.append(
                f"{item_name}: direct CBM was provided, so CBM was used instead of estimating dimensions."
            )

            if catalog_match:
                issues.append(
                    f"{item_name}: handling properties were matched from catalog item '{matched_name}' with confidence {score:.2f}."
                )

            continue

        if "quantity" not in raw_item:
            unresolved_items.append(raw_item)
            issues.append(f"{item_name}: missing quantity.")
            continue

        if _has_dimensions(raw_item):
            resolved_items.append(raw_item)
            continue

        if catalog_match is None:
            unresolved_items.append(raw_item)
            issues.append(
                f"{item_name}: missing dimensions and no catalog match found. "
                "Length, width, and height are required for CBM calculation."
            )
            continue

        resolved_items.append(_merge_with_catalog(raw_item, catalog_match))
        issues.append(
            f"{item_name}: dimensions and handling properties were estimated from catalog item "
            f"'{matched_name}' with confidence {score:.2f}."
        )

    return {
        "resolved_items": resolved_items,
        "unresolved_items": unresolved_items,
        "issues": issues,
    }
