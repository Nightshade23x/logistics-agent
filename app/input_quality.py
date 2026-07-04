from __future__ import annotations

from typing import Any


def _quality_level(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 60:
        return "needs_review"
    return "poor"


def assess_input_quality(item_breakdown: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Checks whether the shipment input looks realistic enough for logistics planning.

    This helps catch common user mistakes such as entering centimetres as metres,
    missing item weights, or providing cargo dimensions that may not fit normal
    container handling.
    """
    score = 100
    warnings: list[str] = []
    recommendations: list[str] = []

    for item in item_breakdown:
        name = item["name"]
        quantity = item["quantity"]
        length = item["length_m"]
        width = item["width_m"]
        height = item["height_m"]
        unit_cbm = item["unit_cbm"]
        weight_kg = item.get("weight_kg", 0)

        largest_dimension = max(length, width, height)

        if largest_dimension > 20:
            score -= 25
            warnings.append(
                f"{name}: one dimension is over 20 m. This is unusually large and may be a unit-entry mistake."
            )
            recommendations.append(
                f"{name}: confirm whether the dimensions were meant to be in cm, mm, inches, feet, or metres."
            )

        elif largest_dimension > 12:
            score -= 15
            warnings.append(
                f"{name}: one dimension is over 12 m, which may exceed normal container loading practicality."
            )
            recommendations.append(
                f"{name}: check whether special equipment, open-top, flat-rack, or breakbulk handling is needed."
            )

        if width > 2.35:
            score -= 10
            warnings.append(
                f"{name}: width is above 2.35 m, which may be difficult for standard container internal width."
            )
            recommendations.append(
                f"{name}: verify packed width and check whether standard container loading is possible."
            )

        if height > 2.7:
            score -= 10
            warnings.append(
                f"{name}: height is above 2.7 m, which may be difficult for standard container internal height."
            )
            recommendations.append(
                f"{name}: check whether a high cube, open-top, or specialist container is needed."
            )

        if unit_cbm > 25:
            score -= 10
            warnings.append(
                f"{name}: unit CBM is very high, so this may be oversized cargo."
            )
            recommendations.append(
                f"{name}: verify whether this is one packed unit or multiple smaller packages."
            )

        if weight_kg == 0:
            score -= 5
            warnings.append(
                f"{name}: item weight is missing or zero."
            )
            recommendations.append(
                f"{name}: add estimated packed weight to improve payload and risk planning."
            )

        if unit_cbm > 0 and weight_kg > 0:
            density = weight_kg / unit_cbm

            if density > 1500:
                score -= 10
                warnings.append(
                    f"{name}: density is very high at about {round(density, 2)} kg/CBM."
                )
                recommendations.append(
                    f"{name}: check floor loading, payload limits, and whether weight distribution needs specialist review."
                )

            elif density < 5:
                score -= 5
                warnings.append(
                    f"{name}: density is very low at about {round(density, 2)} kg/CBM."
                )
                recommendations.append(
                    f"{name}: verify weight because very light bulky cargo can affect space planning."
                )

        if quantity >= 1000 and unit_cbm >= 0.1:
            score -= 5
            warnings.append(
                f"{name}: high quantity with meaningful unit CBM may create a large-volume shipment."
            )
            recommendations.append(
                f"{name}: confirm quantity and whether items are packed individually or consolidated."
            )

    score = max(score, 0)

    if not warnings:
        warnings.append("No major input quality issues detected.")

    if not recommendations:
        recommendations.append("Input data looks suitable for first-pass logistics planning.")

    return {
        "quality_level": _quality_level(score),
        "quality_score": score,
        "warnings": warnings,
        "recommendations": recommendations,
    }
