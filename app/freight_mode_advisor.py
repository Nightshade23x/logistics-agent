from __future__ import annotations

from typing import Any


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
    return " ".join(str(value).split())


def _get_logistics_response(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    specialist_responses = user_agent_response.get("specialist_responses", {})

    if not isinstance(specialist_responses, dict):
        return {}

    logistics_response = specialist_responses.get("logistics_agent", {})

    if isinstance(logistics_response, dict):
        return logistics_response

    return {}


def _get_handoff_payload(logistics_response: dict[str, Any]) -> dict[str, Any]:
    handoff_payload = logistics_response.get("handoff_payload", {})

    if isinstance(handoff_payload, dict):
        return handoff_payload

    return {}


def build_freight_mode_advice(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    logistics_response = _get_logistics_response(user_agent_response)
    handoff_payload = _get_handoff_payload(logistics_response)

    total_cbm = _as_float(handoff_payload.get("total_cbm"))
    total_weight_kg = _as_float(handoff_payload.get("total_weight_kg"))
    recommended_load_type = str(handoff_payload.get("recommended_load_type", "")).lower()
    recommended_container = handoff_payload.get("recommended_container")
    cargo_categories = {
        str(category).lower()
        for category in _as_list(handoff_payload.get("cargo_categories"))
    }

    special_cases: set[str] = set()

    special_handling = handoff_payload.get("special_handling", {})
    if isinstance(special_handling, dict):
        special_cases.update(
            str(case).lower()
            for case in _as_list(special_handling.get("detected_special_cases"))
        )

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    mode_options: list[dict[str, Any]] = []

    if total_cbm is None or total_weight_kg is None:
        return {
            "applicable": False,
            "status": "needs_more_information",
            "summary": "Freight mode advice needs total CBM and total weight.",
            "primary_mode": None,
            "mode_options": [],
            "blockers": ["Total CBM or total weight is missing."],
            "warnings": [],
            "recommendations": [
                "Confirm packed dimensions and gross shipment weight before choosing freight mode."
            ],
        }

    if total_cbm <= 0 or total_weight_kg <= 0:
        return {
            "applicable": False,
            "status": "blocked",
            "summary": "Freight mode advice cannot run with invalid cargo size or weight.",
            "primary_mode": None,
            "mode_options": [],
            "blockers": ["Total CBM or total weight is invalid."],
            "warnings": [],
            "recommendations": [
                "Fix shipment dimensions and weight before selecting freight mode."
            ],
        }

    if "hazardous" in cargo_categories or "hazardous_cargo" in special_cases:
        blockers.append("Hazardous cargo requires carrier acceptance and dangerous goods checks before mode selection.")
        recommendations.append("Run compliance and carrier dangerous-goods approval before booking.")

    if "temperature_control" in special_cases or "refrigerated" in cargo_categories:
        warnings.append("Temperature-sensitive cargo may require reefer or cold-chain service.")
        recommendations.append("Confirm temperature range, reefer requirement, and allowed time outside temperature control.")

    if total_cbm >= 15 or "fcl" in recommended_load_type:
        primary_mode = "sea_fcl"
        mode_options.append(
            {
                "mode": "sea_fcl",
                "fit": "strong",
                "reason": "Cargo volume is suitable for full-container-load planning.",
            }
        )
        mode_options.append(
            {
                "mode": "sea_lcl",
                "fit": "possible_but_less_preferred",
                "reason": "LCL is possible but may be less attractive for larger volume and mixed fragile cargo.",
            }
        )
        mode_options.append(
            {
                "mode": "air_freight",
                "fit": "weak",
                "reason": "Shipment size and weight are likely too large for cost-effective standard air freight.",
            }
        )
        recommendations.append("Compare FCL quotes for 20ft, 40ft, and 40ft high cube containers.")

    elif total_cbm < 15 and total_weight_kg < 3000:
        primary_mode = "sea_lcl"
        mode_options.append(
            {
                "mode": "sea_lcl",
                "fit": "strong",
                "reason": "Cargo is below typical FCL volume and can be consolidated.",
            }
        )
        mode_options.append(
            {
                "mode": "sea_fcl",
                "fit": "possible",
                "reason": "FCL may still be useful if cargo needs better control or lower handling risk.",
            }
        )
        mode_options.append(
            {
                "mode": "air_freight",
                "fit": "possible_if_urgent",
                "reason": "Air freight may be considered if the shipment is urgent and budget allows.",
            }
        )
        recommendations.append("Compare LCL cost against a small FCL option if cargo is fragile or high-value.")

    else:
        primary_mode = "sea_freight_review_required"
        mode_options.append(
            {
                "mode": "sea_freight",
                "fit": "review_required",
                "reason": "Cargo size or weight needs a quote-based decision.",
            }
        )
        recommendations.append("Request freight quotes before final mode selection.")

    if "fragile" in cargo_categories or "fragile_cargo" in special_cases:
        warnings.append("Fragile cargo increases handling risk, especially for LCL transshipment.")
        recommendations.append("Prefer modes with fewer handling points when fragile cargo is significant.")

    if "battery_possible" in special_cases:
        warnings.append("Battery cargo may be restricted by air carriers and some sea carriers.")
        recommendations.append("Confirm battery documents and carrier acceptance before choosing air freight.")

    if recommended_container:
        recommendations.append(f"Use the logistics container recommendation as a quote baseline: {recommended_container}.")

    if blockers:
        status = "blocked"
        summary = "Freight mode advice found blockers before booking."
    elif warnings:
        status = "review_required"
        summary = "Freight mode advice is usable but needs review before booking."
    else:
        status = "clear"
        summary = "Freight mode advice is clear for first-pass planning."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "primary_mode": primary_mode,
        "total_cbm": total_cbm,
        "total_weight_kg": total_weight_kg,
        "mode_options": mode_options,
        "blockers": list(dict.fromkeys(_clean_text(item) for item in blockers)),
        "warnings": list(dict.fromkeys(_clean_text(item) for item in warnings)),
        "recommendations": list(dict.fromkeys(_clean_text(item) for item in recommendations)),
    }
