from __future__ import annotations

from typing import Any


def _collect_categories(item_breakdown: list[dict[str, Any]]) -> set[str]:
    return {
        category
        for item in item_breakdown
        for category in item.get("cargo_categories", [])
    }


def _has_large_non_stackable_cargo(item_breakdown: list[dict[str, Any]]) -> bool:
    for item in item_breakdown:
        categories = item.get("cargo_categories", [])
        if "non_stackable" in categories and item.get("total_cbm", 0) >= 5:
            return True

    return False


def recommend_container_strategy(
    item_breakdown: list[dict[str, Any]],
    container_recommendation: dict[str, Any],
) -> dict[str, Any]:
    """
    Recommends the practical container/handling strategy after the base
    CBM and weight container recommendation has been made.
    """
    categories = _collect_categories(item_breakdown)
    utilization = container_recommendation.get("estimated_utilization_percent")

    strategy_type = "standard_container"
    priority = "normal"
    recommendations: list[str] = []
    warnings: list[str] = []

    if "radioactive" in categories:
        strategy_type = "regulated_specialist_cargo"
        priority = "critical"
        warnings.append(
            "Radioactive cargo cannot be moved using normal container planning."
        )
        recommendations.append(
            "Use a licensed specialist carrier and obtain regulatory approval before shipment."
        )

    elif "hazardous" in categories:
        strategy_type = "dangerous_goods_container_handling"
        priority = "high"
        warnings.append(
            "Hazardous cargo may require dangerous goods documentation, labelling, and segregation."
        )
        recommendations.append(
            "Confirm dangerous goods class and use approved packing/segregation procedures."
        )

    elif "perishable" in categories:
        strategy_type = "refrigerated_or_temperature_controlled"
        priority = "high"
        warnings.append(
            "Perishable cargo may spoil if exposed to delays or unsuitable temperature conditions."
        )
        recommendations.append(
            "Consider a refrigerated container or temperature-controlled route."
        )

    if "fragile" in categories:
        recommendations.append(
            "Use crates, corner protection, cushioning, and fragile labelling for breakable cargo."
        )

    if "heavy" in categories:
        recommendations.append(
            "Plan floor loading carefully and distribute heavy cargo evenly across the container."
        )

    if "non_stackable" in categories:
        recommendations.append(
            "Reserve enough floor space because non-stackable cargo reduces vertical space usage."
        )

    if _has_large_non_stackable_cargo(item_breakdown):
        warnings.append(
            "Large non-stackable cargo is present, so CBM alone may overestimate usable capacity."
        )
        recommendations.append(
            "Check actual item footprints and loading orientation before confirming the booking."
        )

    if isinstance(utilization, (int, float)) and utilization >= 80:
        warnings.append(
            "The recommended container is highly utilized, leaving limited space for loading gaps."
        )
        recommendations.append(
            "Consider a larger container or split shipment if packaging dimensions are uncertain."
        )

    if not recommendations:
        recommendations.append(
            "Standard dry container handling appears suitable based on the current item data."
        )

    if not warnings:
        warnings.append(
            "No special container strategy warnings detected from the current cargo profile."
        )

    return {
        "strategy_type": strategy_type,
        "priority": priority,
        "warnings": warnings,
        "recommendations": recommendations,
    }
