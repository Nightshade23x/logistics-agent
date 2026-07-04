from __future__ import annotations

from itertools import permutations
from typing import Any


CONTAINER_INTERNAL_SPECS = {
    "20ft Standard Container": {
        "internal_length_m": 5.9,
        "internal_width_m": 2.35,
        "internal_height_m": 2.39,
        "door_width_m": 2.34,
        "door_height_m": 2.28,
    },
    "40ft Standard Container": {
        "internal_length_m": 12.03,
        "internal_width_m": 2.35,
        "internal_height_m": 2.39,
        "door_width_m": 2.34,
        "door_height_m": 2.28,
    },
    "40ft High Cube Container": {
        "internal_length_m": 12.03,
        "internal_width_m": 2.35,
        "internal_height_m": 2.69,
        "door_width_m": 2.34,
        "door_height_m": 2.58,
    },
}


def _extract_container_name(container_recommendation: dict[str, Any]) -> str | None:
    possible_keys = [
        "recommended_container",
        "container_name",
        "name",
        "selected_container",
    ]

    for key in possible_keys:
        value = container_recommendation.get(key)
        if isinstance(value, str) and value in CONTAINER_INTERNAL_SPECS:
            return value

    recommendation_text = str(container_recommendation)

    for container_name in CONTAINER_INTERNAL_SPECS:
        if container_name in recommendation_text:
            return container_name

    return None


def _fits_inside_container(
    length: float,
    width: float,
    height: float,
    container_spec: dict[str, float],
) -> bool:
    item_dimensions = [length, width, height]

    for item_length, item_width, item_height in permutations(item_dimensions):
        if (
            item_length <= container_spec["internal_length_m"]
            and item_width <= container_spec["internal_width_m"]
            and item_height <= container_spec["internal_height_m"]
        ):
            return True

    return False


def _fits_through_door(
    length: float,
    width: float,
    height: float,
    container_spec: dict[str, float],
) -> bool:
    item_dimensions = [length, width, height]

    for _, door_width_side, door_height_side in permutations(item_dimensions):
        if (
            door_width_side <= container_spec["door_width_m"]
            and door_height_side <= container_spec["door_height_m"]
        ):
            return True

    return False


def _smallest_standard_fit(length: float, width: float, height: float) -> str | None:
    for container_name in [
        "20ft Standard Container",
        "40ft Standard Container",
        "40ft High Cube Container",
    ]:
        spec = CONTAINER_INTERNAL_SPECS[container_name]

        if _fits_inside_container(length, width, height, spec) and _fits_through_door(
            length,
            width,
            height,
            spec,
        ):
            return container_name

    return None


def assess_container_fit(
    item_breakdown: list[dict[str, Any]],
    container_recommendation: dict[str, Any],
) -> dict[str, Any]:
    selected_container = _extract_container_name(container_recommendation)

    if selected_container:
        selected_spec = CONTAINER_INTERNAL_SPECS[selected_container]
    else:
        selected_spec = CONTAINER_INTERNAL_SPECS["40ft High Cube Container"]

    item_fit_results: list[dict[str, Any]] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    specialist_required = False
    review_required = False

    for item in item_breakdown:
        name = item["name"]
        length = item["length_m"]
        width = item["width_m"]
        height = item["height_m"]

        fits_selected = _fits_inside_container(length, width, height, selected_spec)
        passes_selected_door = _fits_through_door(length, width, height, selected_spec)
        smallest_standard_fit = _smallest_standard_fit(length, width, height)

        if not fits_selected or not passes_selected_door:
            review_required = True

            warnings.append(
                f"{name}: may not physically fit inside or through the door of the selected container."
            )

            if smallest_standard_fit:
                recommendations.append(
                    f"{name}: check whether switching to {smallest_standard_fit} solves the physical fit issue."
                )
            else:
                specialist_required = True
                recommendations.append(
                    f"{name}: does not appear to fit standard closed containers. Check open-top, flat-rack, breakbulk, or specialist cargo handling."
                )

        item_fit_results.append(
            {
                "item_name": name,
                "quantity": item["quantity"],
                "dimensions_m": {
                    "length": length,
                    "width": width,
                    "height": height,
                },
                "fits_selected_container": fits_selected,
                "passes_selected_container_door": passes_selected_door,
                "smallest_standard_container_fit": smallest_standard_fit,
            }
        )

    if not warnings:
        warnings.append("No major physical container fit issues detected.")

    if not recommendations:
        recommendations.append("Cargo appears physically suitable for standard container loading.")

    if specialist_required:
        fit_status = "specialist_required"
    elif review_required:
        fit_status = "review_required"
    else:
        fit_status = "fits_selected_container"

    return {
        "fit_status": fit_status,
        "selected_container_checked": selected_container or "40ft High Cube Container fallback check",
        "note": "Container dimensions are approximate. Final loading must be verified against carrier-specific container dimensions.",
        "warnings": warnings,
        "recommendations": recommendations,
        "item_fit_results": item_fit_results,
    }
