from __future__ import annotations

from typing import Any


def _zone_for_item(item: dict[str, Any]) -> str:
    categories = set(item.get("categories", []))
    suggested_zone = item.get("suggested_zone", "").lower()

    if "radioactive" in categories:
        return "regulated_isolation_zone"

    if "hazardous" in categories:
        return "separated_hazardous_zone"

    if "door" in suggested_zone or "close to the door" in suggested_zone:
        return "door_access_zone"

    if "heavy" in categories or "bottom" in suggested_zone or "base" in suggested_zone:
        return "front_floor_base_zone"

    if "fragile" in categories:
        return "protected_middle_zone"

    if "non_stackable" in categories:
        return "side_floor_zone"

    return "general_stackable_zone"


def _zone_description(zone: str) -> str:
    descriptions = {
        "front_floor_base_zone": "Front/base floor area for heavy cargo and stable weight distribution.",
        "protected_middle_zone": "Middle protected area for fragile cargo with cushioning and reduced pressure.",
        "door_access_zone": "Near-door area for items that should be unloaded first or handled carefully.",
        "side_floor_zone": "Side/floor area reserved for non-stackable items.",
        "general_stackable_zone": "Remaining space for general stackable cargo.",
        "separated_hazardous_zone": "Separated zone for hazardous goods, subject to compliance checks.",
        "regulated_isolation_zone": "Special isolation zone for regulated cargo; specialist planning required.",
    }

    return descriptions.get(zone, "General container zone.")


def generate_container_layout(
    loading_sequence: list[dict[str, Any]],
    container_recommendation: dict[str, Any],
) -> dict[str, Any]:
    """
    Creates a simple zone-based layout plan.

    This is not a full 3D bin-packing algorithm. It is a practical first-step
    layout plan that can later be replaced or enhanced with a visual packing API.
    """
    zones: dict[str, list[dict[str, Any]]] = {}

    for item in loading_sequence:
        zone = _zone_for_item(item)

        zones.setdefault(zone, []).append(
            {
                "item_name": item["item_name"],
                "quantity": item["quantity"],
                "sequence_number": item["sequence_number"],
                "reason": item["reason"],
            }
        )

    ordered_zone_names = [
        "front_floor_base_zone",
        "side_floor_zone",
        "protected_middle_zone",
        "general_stackable_zone",
        "door_access_zone",
        "separated_hazardous_zone",
        "regulated_isolation_zone",
    ]

    layout_zones = []

    for zone_name in ordered_zone_names:
        if zone_name not in zones:
            continue

        layout_zones.append(
            {
                "zone_name": zone_name,
                "description": _zone_description(zone_name),
                "items": zones[zone_name],
            }
        )

    layout_notes = [
        "This is a rule-based zone layout, not a final 3D packing result.",
        "Actual loading should be verified using final packed dimensions, weights, and packaging type.",
        "Heavy cargo should be secured to prevent movement during transport.",
        "Fragile cargo should be protected from compression, vibration, and direct contact with heavy cargo.",
    ]

    if container_recommendation["container_name"] == "Multiple containers or specialist planning required":
        layout_notes.append(
            "Because the shipment may exceed standard limits, the layout must be reviewed by a specialist planner."
        )

    return {
        "layout_type": "rule_based_zone_layout",
        "container": container_recommendation["container_name"],
        "zones": layout_zones,
        "layout_notes": layout_notes,
    }
