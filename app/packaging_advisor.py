from __future__ import annotations

from typing import Any


def _risk_level(score: int) -> str:
    if score >= 8:
        return "critical"
    if score >= 5:
        return "high"
    if score >= 3:
        return "moderate"
    return "low"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def _recommend_for_item(item: dict[str, Any]) -> dict[str, Any]:
    name = item["name"]
    categories = set(item.get("cargo_categories", []))

    packaging_actions: list[str] = []
    securing_actions: list[str] = []
    labels: list[str] = []
    materials: list[str] = []
    score = 0

    if "fragile" in categories:
        score += 3
        packaging_actions.extend(
            [
                "Use reinforced cartons, crates, or original manufacturer packaging where possible.",
                "Add cushioning around all sides using foam, bubble wrap, or air pillows.",
                "Use corner protection for edges and screens.",
                "Avoid placing heavy cargo above or directly against this item.",
            ]
        )
        securing_actions.append(
            "Place in a protected zone and prevent movement using dunnage or straps."
        )
        labels.extend(["FRAGILE", "HANDLE WITH CARE"])
        materials.extend(["reinforced cartons/crates", "foam cushioning", "corner protectors"])

    if "heavy" in categories:
        score += 2
        packaging_actions.append(
            "Use strong outer packaging or palletization suitable for the item weight."
        )
        securing_actions.extend(
            [
                "Load on the floor/base layer and distribute weight evenly.",
                "Use straps, chocks, or blocking to prevent shifting during transport.",
            ]
        )
        labels.append("HEAVY")
        materials.extend(["pallets if suitable", "straps", "blocking/chocking materials"])

    if "non_stackable" in categories:
        score += 2
        packaging_actions.append(
            "Mark as non-stackable and reserve floor space."
        )
        securing_actions.append(
            "Do not place other cargo on top of this item."
        )
        labels.append("DO NOT STACK")

    if "perishable" in categories:
        score += 3
        packaging_actions.extend(
            [
                "Use temperature-suitable packaging.",
                "Confirm maximum allowed transit time before dispatch.",
            ]
        )
        securing_actions.append(
            "Keep accessible for temperature checks where operationally possible."
        )
        labels.extend(["PERISHABLE", "TEMPERATURE SENSITIVE"])
        materials.extend(["insulated packaging", "temperature monitoring device if required"])

    if "hazardous" in categories:
        score += 4
        packaging_actions.append(
            "Use approved hazardous-goods packaging only after confirming the cargo class."
        )
        securing_actions.append(
            "Segregate from incompatible cargo and follow dangerous goods handling rules."
        )
        labels.extend(["HAZARDOUS", "SPECIAL HANDLING REQUIRED"])
        materials.append("approved hazardous-goods packaging")

    if "radioactive" in categories:
        score += 5
        packaging_actions.append(
            "Do not pack as normal cargo; use specialist approved radioactive-material packaging."
        )
        securing_actions.append(
            "Use licensed specialist handling and regulatory clearance before loading."
        )
        labels.extend(["RADIOACTIVE", "REGULATED CARGO"])
        materials.append("approved radioactive-material packaging")

    if not packaging_actions:
        packaging_actions.append(
            "Use standard export-quality packaging suitable for container movement."
        )
        securing_actions.append(
            "Secure cargo so it does not shift during transport."
        )
        labels.append("GENERAL CARGO")
        materials.append("standard export cartons or wrapping")

    return {
        "item_name": name,
        "quantity": item["quantity"],
        "risk_level": _risk_level(score),
        "packaging_actions": _unique(packaging_actions),
        "securing_actions": _unique(securing_actions),
        "recommended_labels": _unique(labels),
        "recommended_materials": _unique(materials),
    }


def generate_packaging_plan(item_breakdown: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Creates item-level packaging and securing recommendations.

    This focuses on physical logistics handling, not insurance pricing or
    legal compliance.
    """
    per_item = [_recommend_for_item(item) for item in item_breakdown]

    all_materials = _unique(
        material
        for item in per_item
        for material in item["recommended_materials"]
    )

    all_labels = _unique(
        label
        for item in per_item
        for label in item["recommended_labels"]
    )

    risk_order = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
    highest_risk = max(
        (item["risk_level"] for item in per_item),
        key=lambda level: risk_order[level],
        default="low",
    )

    general_notes = [
        "Use export-quality packaging because container cargo experiences vibration, pressure, and movement.",
        "Confirm that packed dimensions match the dimensions used for CBM calculation.",
        "Photograph packed cargo before loading for evidence and insurance support.",
        "Use dunnage to fill gaps and reduce movement inside the container.",
    ]

    return {
        "packaging_risk_level": highest_risk,
        "recommended_materials": all_materials,
        "recommended_labels": all_labels,
        "per_item_packaging": per_item,
        "general_notes": general_notes,
    }
