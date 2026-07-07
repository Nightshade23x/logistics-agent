from __future__ import annotations

from typing import Any


BATTERY_MARKERS = [
    "lithium",
    "battery",
    "batteries",
    "power bank",
    "powerbank",
    "electric scooter",
    "e-scooter",
    "scooter",
    "e-bike",
    "ebike",
    "laptop",
    "phone",
]

FRAGILE_MARKERS = [
    "tv",
    "television",
    "screen",
    "monitor",
    "glass",
    "ceramic",
    "tile",
    "tiles",
    "mirror",
    "display",
]

HAZARDOUS_MARKERS = [
    "hazardous",
    "dangerous goods",
    "flammable",
    "explosive",
    "aerosol",
    "paint",
    "solvent",
    "chemical",
    "acid",
    "fuel",
    "gas cylinder",
]

TEMPERATURE_MARKERS = [
    "refrigerated",
    "frozen",
    "chilled",
    "perishable",
    "medicine",
    "vaccine",
    "food",
    "seafood",
    "meat",
    "dairy",
]

OVERSIZE_MARKERS = [
    "oversize",
    "oversized",
    "machinery",
    "industrial machine",
    "generator",
    "engine",
    "vehicle",
]


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _clean_text(value: Any) -> str:
    return " ".join(str(value).split())


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _get_nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})

    if isinstance(value, dict):
        return value

    return {}


def _extract_item_lists(container: dict[str, Any]) -> list[dict[str, Any]]:
    item_keys = [
        "items",
        "selected_items",
        "shipment_items",
        "cargo_items",
        "products",
    ]

    items: list[dict[str, Any]] = []

    for key in item_keys:
        for item in _as_list(container.get(key)):
            if isinstance(item, dict):
                items.append(item)

    return items


def _extract_items(user_agent_response: dict[str, Any]) -> list[dict[str, Any]]:
    specialist_responses = _get_nested_dict(user_agent_response, "specialist_responses")

    candidate_containers: list[dict[str, Any]] = []

    for agent_name in ["logistics_agent", "shopping_agent", "document_ai_agent"]:
        agent_response = specialist_responses.get(agent_name, {})

        if not isinstance(agent_response, dict):
            continue

        candidate_containers.append(agent_response)

        handoff_payload = agent_response.get("handoff_payload", {})
        if isinstance(handoff_payload, dict):
            candidate_containers.append(handoff_payload)

    top_level_handoff = user_agent_response.get("handoff_payload", {})
    if isinstance(top_level_handoff, dict):
        candidate_containers.append(top_level_handoff)

    items: list[dict[str, Any]] = []

    for container in candidate_containers:
        items.extend(_extract_item_lists(container))

    unique_items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        identity = repr(sorted(item.items()))

        if identity in seen:
            continue

        unique_items.append(item)
        seen.add(identity)

    return unique_items


def _item_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("product_name"),
        item.get("name"),
        item.get("item_name"),
        item.get("description"),
        item.get("product_category"),
        item.get("category"),
        item.get("cargo_category"),
    ]

    return " ".join(_clean_text(part) for part in parts if part)


def build_cargo_special_handling_review(
    user_agent_response: dict[str, Any],
) -> dict[str, Any]:
    items = _extract_items(user_agent_response)

    if not items:
        return {
            "applicable": False,
            "status": "not_applicable",
            "summary": "No cargo items were available for special handling review.",
            "item_count": 0,
            "detected_special_cases": [],
            "blockers": [],
            "warnings": [],
            "recommendations": [],
        }

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    detected_special_cases: list[str] = []

    for item in items:
        item_name = (
            item.get("product_name")
            or item.get("name")
            or item.get("item_name")
            or "Unnamed item"
        )

        item_name = _clean_text(item_name)
        searchable_text = _item_text(item)

        unit_weight_kg = _as_float(
            item.get("unit_weight_kg")
            or item.get("weight_kg")
            or item.get("weight")
        )

        if _contains_any(searchable_text, BATTERY_MARKERS):
            detected_special_cases.append("battery_possible")
            warnings.append(
                f"{item_name}: may contain lithium batteries or battery components."
            )
            recommendations.append(
                f"{item_name}: confirm battery type, battery watt-hours, MSDS, UN38.3 status, and carrier acceptance before booking."
            )

        if _contains_any(searchable_text, FRAGILE_MARKERS):
            detected_special_cases.append("fragile_cargo")
            warnings.append(f"{item_name}: fragile cargo handling is required.")
            recommendations.append(
                f"{item_name}: use corner protection, cushioning, strong cartons or crates, and avoid loading heavy cargo on top."
            )

        if _contains_any(searchable_text, HAZARDOUS_MARKERS):
            detected_special_cases.append("hazardous_cargo")
            blockers.append(
                f"{item_name}: appears to be hazardous or dangerous goods cargo."
            )
            recommendations.append(
                f"{item_name}: confirm dangerous goods classification, documentation, packaging, labels, and carrier approval before proceeding."
            )

        if _contains_any(searchable_text, TEMPERATURE_MARKERS):
            detected_special_cases.append("temperature_control")
            temperature_controlled = bool(
                item.get("temperature_controlled")
                or item.get("requires_temperature_control")
                or item.get("reefer_required")
            )

            if not temperature_controlled:
                blockers.append(
                    f"{item_name}: appears temperature-sensitive but no temperature-control requirement was confirmed."
                )
                recommendations.append(
                    f"{item_name}: confirm temperature range, reefer requirement, and maximum allowed time outside temperature control."
                )

        if _contains_any(searchable_text, OVERSIZE_MARKERS):
            detected_special_cases.append("oversize_or_heavy_cargo")
            warnings.append(
                f"{item_name}: may require oversize or heavy-cargo planning."
            )
            recommendations.append(
                f"{item_name}: confirm packed dimensions, lifting points, lashing requirements, and whether flat-rack or special equipment is needed."
            )

        if unit_weight_kg is not None and unit_weight_kg >= 100:
            detected_special_cases.append("heavy_unit")
            warnings.append(f"{item_name}: each unit weighs {unit_weight_kg} kg.")
            recommendations.append(
                f"{item_name}: confirm forklift/crane availability and floor loading limits at origin and destination."
            )

    unique_blockers = list(dict.fromkeys(blockers))
    unique_warnings = list(dict.fromkeys(warnings))
    unique_recommendations = list(dict.fromkeys(recommendations))
    unique_cases = sorted(set(detected_special_cases))

    if unique_blockers:
        status = "blocked"
        summary = "Special cargo review found blockers before shipment booking."
    elif unique_warnings:
        status = "review_required"
        summary = "Special cargo review found handling requirements that need review."
    else:
        status = "clear"
        summary = "No special cargo handling issues were detected."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "item_count": len(items),
        "detected_special_cases": unique_cases,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "recommendations": unique_recommendations,
    }
