from __future__ import annotations

from typing import Any


def _get_loading_stage(categories: list[str], unload_priority: int) -> int:
    """
    Lower stage means loaded earlier.
    Heavy/non-stackable items should usually go first.
    Fragile high-priority items should be closer to the door and loaded later.
    """
    if "radioactive" in categories or "hazardous" in categories:
        return 0

    if "heavy" in categories and "non_stackable" in categories:
        return 1

    if "heavy" in categories:
        return 2

    if "non_stackable" in categories:
        return 3

    if "fragile" in categories and unload_priority == 1:
        return 6

    if "fragile" in categories:
        return 5

    if unload_priority == 1:
        return 6

    return 4


def _suggest_zone(categories: list[str], unload_priority: int) -> str:
    if "radioactive" in categories:
        return "Special regulated isolation zone"

    if "hazardous" in categories:
        return "Separated hazardous cargo zone"

    if "heavy" in categories and "non_stackable" in categories:
        return "Bottom floor zone, evenly distributed and secured"

    if "heavy" in categories:
        return "Bottom/base layer, spread across the container floor"

    if "non_stackable" in categories:
        return "Floor space or side-wall zone with no cargo stacked above"

    if "fragile" in categories and unload_priority == 1:
        return "Protected area close to the door for careful unloading"

    if "fragile" in categories:
        return "Protected middle/top zone with cushioning"

    if unload_priority == 1:
        return "Door-accessible zone"

    return "General stackable cargo zone"


def _build_reason(item: dict[str, Any]) -> str:
    categories = item["cargo_categories"]
    reasons: list[str] = []

    if "heavy" in categories:
        reasons.append("heavy cargo should support the load from the bottom")

    if "fragile" in categories:
        reasons.append("fragile cargo needs protection from pressure and impact")

    if "non_stackable" in categories:
        reasons.append("non-stackable cargo should not have items placed above it")

    if "perishable" in categories:
        reasons.append("perishable cargo may need temperature control and fast access")

    if "hazardous" in categories:
        reasons.append("hazardous cargo needs segregation and compliance checks")

    if "radioactive" in categories:
        reasons.append("radioactive cargo requires specialist regulated handling")

    if item.get("unload_priority") == 1:
        reasons.append("high unload priority means it should be easier to access")

    if not reasons:
        reasons.append("general cargo can be used to fill remaining space efficiently")

    return "; ".join(reasons) + "."


def generate_loading_sequence(item_breakdown: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Creates a practical loading sequence based on cargo category, stackability,
    weight, fragility, and unload priority.
    """
    planned_items: list[dict[str, Any]] = []

    for item in item_breakdown:
        categories = item["cargo_categories"]
        unload_priority = item.get("unload_priority", 3)

        planned_items.append(
            {
                "item_name": item["name"],
                "quantity": item["quantity"],
                "loading_stage": _get_loading_stage(categories, unload_priority),
                "suggested_zone": _suggest_zone(categories, unload_priority),
                "categories": categories,
                "reason": _build_reason(item),
            }
        )

    planned_items.sort(
        key=lambda item: (
            item["loading_stage"],
            -len(item["categories"]),
            item["item_name"],
        )
    )

    for index, item in enumerate(planned_items, start=1):
        item["sequence_number"] = index

    return planned_items
