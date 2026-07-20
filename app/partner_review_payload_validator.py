from __future__ import annotations

from typing import Any


def _has_value(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str) and not value.strip():
        return False

    return True


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("selected_items"), list):
        return payload["selected_items"]

    if isinstance(payload.get("items"), list):
        return payload["items"]

    return []


def _item_name(item: dict[str, Any]) -> Any:
    return item.get("product_name") or item.get("name")


def _item_quantity(item: dict[str, Any]) -> Any:
    return item.get("requested_quantity") or item.get("quantity")


def _item_value(item: dict[str, Any]) -> Any:
    return item.get("estimated_total_cost_usd") or item.get("declared_value_usd")


def validate_partner_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(payload, dict):
        return {
            "is_valid": False,
            "errors": ["Partner review payload must be a dictionary."],
            "warnings": [],
        }

    origin = payload.get("origin") or payload.get("origin_country")
    destination = payload.get("destination") or payload.get("destination_country")
    items = _extract_items(payload)

    if not _has_value(origin):
        warnings.append("Missing origin country.")

    if not _has_value(destination):
        errors.append("Missing destination country.")

    if not items:
        errors.append("Missing item list.")

    if not _has_value(payload.get("total_cbm")):
        warnings.append("Missing total_cbm.")

    if not _has_value(payload.get("total_weight_kg")):
        warnings.append("Missing total_weight_kg.")

    if not _has_value(payload.get("declared_value_usd")):
        warnings.append("Missing declared_value_usd.")

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"Item {index} must be a dictionary.")
            continue

        name = _item_name(item)
        quantity = _item_quantity(item)
        category = item.get("category") or item.get("product_category")
        item_value = _item_value(item)

        if not _has_value(name):
            errors.append(f"Item {index} is missing product name.")

        if not _has_value(quantity):
            warnings.append(f"Item {index} is missing quantity.")

        if not _has_value(category):
            warnings.append(f"Item {index} is missing category.")

        if not _has_value(item_value):
            warnings.append(f"Item {index} is missing declared or estimated value.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "item_count": len(items),
        "origin": origin,
        "destination": destination,
    }
