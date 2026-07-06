from __future__ import annotations

from typing import Any


def _get_logistics_response(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    specialist_responses = user_agent_response.get("specialist_responses", {})
    logistics_response = specialist_responses.get("logistics_agent", {})

    if isinstance(logistics_response, dict):
        return logistics_response

    return {}


def _get_handoff_payload(logistics_response: dict[str, Any]) -> dict[str, Any]:
    handoff_payload = logistics_response.get("handoff_payload", {})

    if isinstance(handoff_payload, dict):
        return handoff_payload

    return {}


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _clean_text(value: Any) -> str:
    text = str(value)

    replacements = {
        "wereestimated": "were estimated",
        "propertieswere": "properties were",
        "abovenon-stackable": "above non-stackable",
        "forfirst-pass": "for first-pass",
        "standardcontainer": "standard container",
        "andfragile": "and fragile",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def build_logistics_quality_review(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    logistics_response = _get_logistics_response(user_agent_response)

    if not logistics_response:
        return {
            "applicable": False,
            "status": "not_applicable",
            "summary": "No Logistics Agent response was found for this request.",
            "blockers": [],
            "warnings": [],
            "recommendations": [],
        }

    handoff_payload = _get_handoff_payload(logistics_response)
    response_status = str(logistics_response.get("status", "")).lower()

    total_cbm = _as_float(handoff_payload.get("total_cbm"))
    total_weight_kg = _as_float(handoff_payload.get("total_weight_kg"))
    recommended_container = handoff_payload.get("recommended_container")
    recommended_load_type = handoff_payload.get("recommended_load_type")
    risk_level = str(handoff_payload.get("risk_level", "")).lower()
    risk_score = _as_float(handoff_payload.get("risk_score"))
    readiness_status = str(handoff_payload.get("readiness_status", "")).lower()
    cargo_categories = {
        str(category).lower()
        for category in _as_list(handoff_payload.get("cargo_categories"))
    }

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    if response_status in {"blocked", "error"}:
        blockers.append(f"Logistics Agent returned status: {response_status}.")

    if response_status == "critical_review_required":
        warnings.append("Logistics Agent marked this shipment as requiring critical review.")

    if readiness_status in {"not_ready", "not_ready_blockers_found"}:
        blockers.append(f"Shipment readiness status is {readiness_status}.")

    if not recommended_container:
        blockers.append("No recommended container was provided.")

    if total_cbm is None or total_cbm <= 0:
        blockers.append("Total CBM is missing or invalid.")

    if total_weight_kg is None or total_weight_kg <= 0:
        blockers.append("Total shipment weight is missing or invalid.")

    if risk_level in {"high", "critical"}:
        warnings.append(f"Logistics risk level is {risk_level}.")
        recommendations.append("Review packaging, loading sequence, cargo separation, and insurance before booking.")

    if risk_score is not None and risk_score >= 6:
        warnings.append(f"Logistics risk score is {risk_score}.")

    if "fragile" in cargo_categories and "heavy" in cargo_categories:
        warnings.append("Shipment contains both fragile and heavy cargo.")
        recommendations.append("Physically separate fragile cargo from heavy cargo and use cushioning or crates.")

    if "non_stackable" in cargo_categories:
        warnings.append("Shipment contains non-stackable cargo.")
        recommendations.append("Reserve floor space and avoid placing cargo above non-stackable items.")

    if "hazardous" in cargo_categories or "radioactive" in cargo_categories:
        blockers.append("Shipment contains hazardous or radioactive cargo requiring specialist handling.")
        recommendations.append("Do not proceed until compliance, carrier acceptance, and handling requirements are confirmed.")

    missing_information = logistics_response.get("missing_information", [])
    if isinstance(missing_information, list):
        for item in missing_information:
            item_text = str(item)
            lowered = item_text.lower()

            if "estimated from catalog" in lowered:
                warnings.append(_clean_text(item_text))

            elif item_text.strip():
                warnings.append(_clean_text(item_text))

    if recommended_load_type:
        recommended_load_type_text = str(recommended_load_type).lower()
        if "fcl" in recommended_load_type_text:
            recommendations.append("Compare FCL quotes for 20ft, 40ft, and 40ft high cube options before booking.")

    if blockers:
        status = "blocked"
        summary = "Logistics plan has blockers that must be resolved before shipment booking."
    elif warnings:
        status = "review_required"
        summary = "Logistics plan is usable for first-pass planning but needs review before booking."
    else:
        status = "clear"
        summary = "Logistics plan is usable for first-pass shipment planning."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "total_cbm": total_cbm,
        "total_weight_kg": total_weight_kg,
        "recommended_container": recommended_container,
        "recommended_load_type": recommended_load_type,
        "risk_level": risk_level or None,
        "risk_score": risk_score,
        "readiness_status": readiness_status or None,
        "cargo_categories": sorted(cargo_categories),
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
    }
