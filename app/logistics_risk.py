from __future__ import annotations

from typing import Any


def _risk_score_to_level(score: int) -> str:
    if score >= 8:
        return "critical"
    if score >= 5:
        return "high"
    if score >= 3:
        return "moderate"
    return "low"


def assess_logistics_risk(
    item_breakdown: list[dict[str, Any]],
    container_recommendation: dict[str, Any],
) -> dict[str, Any]:
    """
    Assesses operational logistics risks related to loading, handling,
    container suitability, and cargo protection.

    This is not a legal/compliance checker. It only focuses on practical
    logistics handling risks.
    """
    warnings: list[str] = []
    requirements: list[str] = []
    risk_score = 0

    all_categories = {
        category
        for item in item_breakdown
        for category in item.get("cargo_categories", [])
    }

    utilization = container_recommendation.get("estimated_utilization_percent")

    if container_recommendation["container_name"] == "Multiple containers or specialist planning required":
        risk_score += 4
        warnings.append(
            "The shipment does not safely fit into the listed standard containers."
        )
        requirements.append(
            "Split the shipment across multiple containers or request specialist container planning."
        )

    if isinstance(utilization, (int, float)) and utilization >= 80:
        risk_score += 2
        warnings.append(
            "Container utilization is high, so loading will require careful space planning."
        )
        requirements.append(
            "Verify actual packaging dimensions before final booking."
        )

    if "radioactive" in all_categories:
        risk_score += 5
        warnings.append(
            "Radioactive cargo cannot be handled as normal cargo."
        )
        requirements.append(
            "Use specialist radioactive cargo handling, approved packaging, and regulatory clearance."
        )

    if "hazardous" in all_categories:
        risk_score += 4
        warnings.append(
            "Hazardous cargo may require segregation, labelling, and special documentation."
        )
        requirements.append(
            "Confirm hazardous goods classification before loading."
        )

    if "perishable" in all_categories:
        risk_score += 3
        warnings.append(
            "Perishable cargo may be damaged by delays or unsuitable temperature conditions."
        )
        requirements.append(
            "Consider refrigerated container handling or faster routing."
        )

    if "fragile" in all_categories:
        risk_score += 2
        warnings.append(
            "Fragile cargo is present and may be damaged by pressure, vibration, or poor stacking."
        )
        requirements.append(
            "Use cushioning, crates, corner protection, and clear fragile labelling."
        )

    if "heavy" in all_categories and "fragile" in all_categories:
        risk_score += 2
        warnings.append(
            "The shipment contains both heavy and fragile cargo, which increases damage risk."
        )
        requirements.append(
            "Physically separate heavy goods from fragile goods during loading."
        )

    if "non_stackable" in all_categories:
        risk_score += 2
        warnings.append(
            "Non-stackable cargo is present and will reduce usable container space."
        )
        requirements.append(
            "Reserve floor space for non-stackable cargo and avoid placing cargo above it."
        )

    if not warnings:
        warnings.append(
            "No major operational loading risks detected from the current item data."
        )

    if not requirements:
        requirements.append(
            "Standard container loading checks are sufficient for this shipment."
        )

    return {
        "risk_level": _risk_score_to_level(risk_score),
        "risk_score": risk_score,
        "warnings": warnings,
        "requirements": requirements,
    }
