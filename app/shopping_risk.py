from __future__ import annotations

from typing import Any


def _risk_level_from_score(score: int) -> str:
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def assess_supplier_option_risk(option: dict[str, Any]) -> dict[str, Any]:
    risk_score = 0
    risk_notes: list[str] = []

    lead_time_days = int(option.get("lead_time_days", 0))
    quality_score = float(option.get("quality_score", 0))
    supplier_rating = float(option.get("supplier_rating", 0))
    category = str(option.get("category", "")).lower()
    country = str(option.get("country", ""))
    is_preferred_country = bool(option.get("is_preferred_country", False))

    if lead_time_days > 25:
        risk_score += 2
        risk_notes.append("Long supplier lead time.")
    elif lead_time_days > 18:
        risk_score += 1
        risk_notes.append("Moderate supplier lead time.")

    if quality_score < 7.5:
        risk_score += 2
        risk_notes.append("Quality score is below preferred level.")
    elif quality_score < 8.0:
        risk_score += 1
        risk_notes.append("Quality score is acceptable but not strong.")

    if supplier_rating < 4.1:
        risk_score += 2
        risk_notes.append("Supplier rating is relatively low.")
    elif supplier_rating < 4.4:
        risk_score += 1
        risk_notes.append("Supplier rating is moderate.")

    if category in {"electronics", "mobility"}:
        risk_score += 1
        risk_notes.append("Product category may require additional compliance or documentation checks.")

    if category == "mobility":
        risk_score += 1
        risk_notes.append("Mobility products may involve battery, safety, or transport restrictions.")

    if category == "glassware":
        risk_score += 1
        risk_notes.append("Fragile goods may require stronger packaging and handling checks.")

    if not is_preferred_country:
        risk_score += 1
        risk_notes.append(f"Supplier country {country} is not marked as a preferred country.")

    if option.get("selection_status") == "not_eligible":
        risk_score += 3
        risk_notes.append("Supplier option is not eligible under current constraints.")

    if option.get("availability_status") != "available":
        risk_score += 3
        risk_notes.append("Supplier option has availability, MOQ, or stock limitations.")

    risk_score = min(risk_score, 10)

    return {
        "risk_score": risk_score,
        "risk_level": _risk_level_from_score(risk_score),
        "risk_notes": risk_notes,
    }


def summarize_procurement_risk(selected_items: list[dict[str, Any]]) -> dict[str, Any]:
    if not selected_items:
        return {
            "overall_risk_score": 0,
            "overall_risk_level": "unknown",
            "highest_risk_items": [],
            "risk_notes": ["No selected supplier items available for risk assessment."],
        }

    highest_score = max(int(item.get("risk_score", 0)) for item in selected_items)

    highest_items = [
        {
            "product_name": item.get("product_name"),
            "supplier_name": item.get("supplier_name"),
            "risk_score": item.get("risk_score"),
            "risk_level": item.get("risk_level"),
        }
        for item in selected_items
        if int(item.get("risk_score", 0)) == highest_score
    ]

    combined_notes = []
    for item in selected_items:
        for note in item.get("risk_notes", []):
            if note not in combined_notes:
                combined_notes.append(note)

    return {
        "overall_risk_score": highest_score,
        "overall_risk_level": _risk_level_from_score(highest_score),
        "highest_risk_items": highest_items,
        "risk_notes": combined_notes,
    }
