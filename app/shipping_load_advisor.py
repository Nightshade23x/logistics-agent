from __future__ import annotations

from typing import Any


FRAGILE_KEYWORDS = {
    "tv",
    "television",
    "glass",
    "bottle",
    "bottles",
    "mirror",
    "ceramic",
    "tiles",
    "screen",
}

HEAVY_KEYWORDS = {
    "tiles",
    "scooter",
    "scooters",
    "machinery",
    "machine",
    "furniture",
    "mattress",
    "mattresses",
}

PERISHABLE_KEYWORDS = {
    "fruit",
    "vegetable",
    "food",
    "meat",
    "fish",
    "flowers",
    "medicine",
}

HAZARDOUS_KEYWORDS = {
    "battery",
    "batteries",
    "chemical",
    "fuel",
    "paint",
    "aerosol",
    "radioactive",
}


def _item_name_contains(name: str, keywords: set[str]) -> bool:
    normalized_name = name.lower()

    return any(keyword in normalized_name for keyword in keywords)


def _collect_categories(item_breakdown: list[dict[str, Any]]) -> set[str]:
    categories: set[str] = set()

    for item in item_breakdown:
        item_categories = item.get("categories", [])
        if isinstance(item_categories, list):
            categories.update(item_categories)

        name = str(item.get("name", item.get("item_name", "")))

        if item.get("fragile") or _item_name_contains(name, FRAGILE_KEYWORDS):
            categories.add("fragile")

        if item.get("perishable") or _item_name_contains(name, PERISHABLE_KEYWORDS):
            categories.add("perishable")

        if item.get("hazardous") or _item_name_contains(name, HAZARDOUS_KEYWORDS):
            categories.add("hazardous")

        if item.get("radioactive"):
            categories.add("radioactive")

        if item.get("stackable") is False:
            categories.add("non_stackable")

        if item.get("weight_kg", 0) >= 30 or _item_name_contains(name, HEAVY_KEYWORDS):
            categories.add("heavy")

    return categories


def _extract_recommended_container(container_recommendation: dict[str, Any]) -> str:
    possible_keys = [
        "recommended_container",
        "container",
        "container_name",
        "name",
        "selected_container",
    ]

    for key in possible_keys:
        value = container_recommendation.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for value in container_recommendation.values():
        if isinstance(value, str) and "container" in value.lower():
            return value

    return "Unknown container"


def _has_special_handling(categories: set[str]) -> bool:
    return bool(
        categories.intersection(
            {
                "hazardous",
                "radioactive",
                "perishable",
            }
        )
    )


def _has_damage_sensitive_cargo(categories: set[str]) -> bool:
    return bool(
        categories.intersection(
            {
                "fragile",
                "non_stackable",
            }
        )
    )


def recommend_shipping_load_type(
    total_cbm: float,
    total_weight_kg: float,
    item_breakdown: list[dict[str, Any]],
    logistics_risk: dict[str, Any],
    container_recommendation: dict[str, Any],
) -> dict[str, Any]:
    """
    Recommends FCL or LCL for shipping/container freight.

    FCL = Full Container Load.
    LCL = Less than Container Load.
    """
    categories = _collect_categories(item_breakdown)
    risk_level = str(logistics_risk.get("risk_level", "low")).lower()
    recommended_container = _extract_recommended_container(container_recommendation)

    warnings: list[str] = []
    recommendations: list[str] = []

    special_handling = _has_special_handling(categories)
    damage_sensitive = _has_damage_sensitive_cargo(categories)

    if "multiple containers" in recommended_container.lower() or "specialist" in recommended_container.lower():
        load_type = "specialist_fcl_review"
        confidence = "high"
        reason = (
            "Shipment exceeds normal single-container planning, so it should be reviewed as FCL or specialist container freight."
        )
        warnings.append(
            "Cargo may require multiple containers or specialist freight planning."
        )
        recommendations.append(
            "Confirm final packed dimensions, total weight, and carrier equipment availability before booking."
        )

    elif special_handling:
        load_type = "fcl_preferred"
        confidence = "high"
        reason = (
            "Special-handling cargo is present, so FCL is preferred to reduce shared-container handling and compliance risk."
        )
        warnings.append(
            "Special-handling cargo may not be suitable for standard LCL consolidation."
        )
        recommendations.append(
            "Ask the freight forwarder whether the cargo can move as LCL or must move as FCL/specialist cargo."
        )

    elif total_cbm >= 15 or total_weight_kg >= 8000:
        load_type = "fcl_preferred"
        confidence = "high"
        reason = (
            "Cargo volume or weight is high enough that FCL is likely more practical than LCL."
        )
        recommendations.append(
            "Compare 20ft, 40ft, and 40ft high cube FCL quotes before booking."
        )

    elif damage_sensitive and total_cbm >= 8:
        load_type = "fcl_preferred"
        confidence = "medium"
        reason = (
            "Cargo is damage-sensitive and has meaningful volume, so FCL is preferred to reduce handling, stacking, and co-loading risk."
        )
        warnings.append(
            "LCL may expose fragile or non-stackable cargo to more handling and shared-container pressure."
        )
        recommendations.append(
            "Use FCL if the budget allows, especially if the goods are high value or difficult to replace."
        )

    elif damage_sensitive:
        load_type = "compare_lcl_fcl"
        confidence = "medium"
        reason = (
            "Cargo is damage-sensitive. LCL may be possible because the shipment is small, but FCL should be compared to reduce handling risk."
        )
        warnings.append(
            "LCL may increase handling, stacking, and co-loading risk for fragile or non-stackable cargo."
        )
        recommendations.append(
            "Compare LCL pricing with a 20ft FCL quote before final booking."
        )

    elif total_cbm <= 10 and total_weight_kg <= 3000 and risk_level in {"low", "moderate"}:
        load_type = "lcl_suitable"
        confidence = "medium"
        reason = (
            "Cargo volume and weight are low, and no major special-handling issues were detected, so LCL may be cost-effective."
        )
        recommendations.append(
            "Request LCL quotes and compare them with a 20ft FCL quote before final booking."
        )

    elif total_cbm <= 12 and risk_level in {"low", "moderate"}:
        load_type = "compare_lcl_fcl"
        confidence = "medium"
        reason = (
            "Cargo may be small enough for LCL, but the cargo profile means FCL should also be compared."
        )
        warnings.append(
            "LCL may be cheaper, but it may increase handling and damage risk."
        )
        recommendations.append(
            "Compare LCL pricing with a 20ft FCL quote and choose based on cost, risk, and delivery deadline."
        )

    else:
        load_type = "fcl_preferred"
        confidence = "medium"
        reason = (
            "Cargo profile is better suited to a dedicated container than shared LCL space."
        )
        recommendations.append(
            "Use FCL planning unless a freight forwarder confirms that LCL is safe and cost-effective."
        )

    if not warnings:
        warnings.append("No major FCL/LCL warning detected.")

    return {
        "recommended_load_type": load_type,
        "confidence": confidence,
        "reason": reason,
        "fcl_meaning": "FCL means Full Container Load: the cargo uses a dedicated container.",
        "lcl_meaning": "LCL means Less than Container Load: the cargo shares container space with other shipments.",
        "warnings": warnings,
        "recommendations": recommendations,
        "decision_inputs": {
            "total_cbm": total_cbm,
            "total_weight_kg": total_weight_kg,
            "risk_level": risk_level,
            "cargo_categories": sorted(categories),
            "recommended_container": recommended_container,
        },
    }
