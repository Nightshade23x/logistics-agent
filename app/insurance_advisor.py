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
    text = str(value)

    replacements = {
        "wereestimated": "were estimated",
        "propertieswere": "properties were",
        "abovenon-stackable": "above non-stackable",
        "cushioning,strong": "cushioning, strong",
        "forthis": "for this",
        "IncotermFOB": "Incoterm FOB",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _get_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _get_specialist_response(
    user_agent_response: dict[str, Any],
    agent_name: str,
) -> dict[str, Any]:
    specialist_responses = _get_dict(user_agent_response.get("specialist_responses"))
    return _get_dict(specialist_responses.get(agent_name))


def _get_handoff_payload(agent_response: dict[str, Any]) -> dict[str, Any]:
    return _get_dict(agent_response.get("handoff_payload"))


def _extract_estimated_cargo_value(user_agent_response: dict[str, Any]) -> float | None:
    shopping_response = _get_specialist_response(user_agent_response, "shopping_agent")
    shopping_handoff = _get_handoff_payload(shopping_response)

    value_candidates = [
        shopping_handoff.get("estimated_total_procurement_cost_usd"),
        shopping_handoff.get("declared_value_usd"),
        shopping_response.get("estimated_total_procurement_cost_usd"),
        user_agent_response.get("declared_value_usd"),
    ]

    partner_review = _get_dict(user_agent_response.get("partner_review"))
    value_candidates.append(partner_review.get("declared_value_usd"))

    for value in value_candidates:
        number = _as_float(value)

        if number is not None and number > 0:
            return number

    return None


def _extract_logistics_context(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    logistics_response = _get_specialist_response(user_agent_response, "logistics_agent")
    logistics_handoff = _get_handoff_payload(logistics_response)

    risk_level = str(logistics_handoff.get("risk_level", "")).lower() or None
    risk_score = _as_float(logistics_handoff.get("risk_score"))

    cargo_categories = {
        str(category).lower()
        for category in _as_list(logistics_handoff.get("cargo_categories"))
    }

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "cargo_categories": cargo_categories,
    }


def _extract_trade_term(user_agent_response: dict[str, Any]) -> str | None:
    trade_terms_advice = _get_dict(user_agent_response.get("trade_terms_advice"))

    incoterm = trade_terms_advice.get("incoterm")
    if incoterm:
        return str(incoterm).upper()

    for source in [
        user_agent_response,
        _get_handoff_payload(_get_specialist_response(user_agent_response, "shopping_agent")),
        _get_handoff_payload(_get_specialist_response(user_agent_response, "logistics_agent")),
        _get_handoff_payload(_get_specialist_response(user_agent_response, "document_ai_agent")),
    ]:
        for key in ["incoterm", "trade_term", "trade_terms", "shipping_term", "shipping_terms"]:
            value = source.get(key)

            if value:
                return str(value).upper()

    return None


def build_insurance_advice(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    estimated_value_usd = _extract_estimated_cargo_value(user_agent_response)
    logistics_context = _extract_logistics_context(user_agent_response)
    incoterm = _extract_trade_term(user_agent_response)

    risk_level = logistics_context["risk_level"]
    risk_score = logistics_context["risk_score"]
    cargo_categories = logistics_context["cargo_categories"]

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    reasons: list[str] = []

    if estimated_value_usd is None:
        warnings.append("Estimated cargo value is missing, so insurance advice is incomplete.")
        recommendations.append("Confirm declared cargo value before choosing insurance cover.")
    else:
        reasons.append(f"Estimated cargo value is {estimated_value_usd} USD.")

    fragile_or_sensitive = bool(
        cargo_categories.intersection(
            {"fragile", "non_stackable", "hazardous", "refrigerated", "temperature_controlled"}
        )
    )

    if fragile_or_sensitive:
        reasons.append("Cargo includes fragile, non-stackable, hazardous, or temperature-sensitive handling categories.")
        recommendations.append("Use cargo insurance that covers damage during loading, transshipment, and final delivery.")

    if risk_level in {"high", "critical"}:
        reasons.append(f"Logistics risk level is {risk_level}.")
        recommendations.append("Treat insurance as strongly recommended before booking.")

    if risk_score is not None and risk_score >= 6:
        reasons.append(f"Logistics risk score is {risk_score}.")
        recommendations.append("Review insurance exclusions before accepting the freight quote.")

    if incoterm in {"CIF", "CIP"}:
        warnings.append(f"Incoterm {incoterm} normally includes seller-arranged insurance, but coverage may be minimum only.")
        recommendations.append("Check whether seller-arranged insurance is enough for the cargo value and fragility.")

    elif incoterm in {"FOB", "FCA", "FAS", "EXW", "CFR", "CPT"}:
        warnings.append(f"Under Incoterm {incoterm}, buyer-side insurance responsibility should be confirmed.")
        recommendations.append("Confirm whether the buyer or seller will purchase cargo insurance.")

    elif incoterm in {"DAP", "DPU", "DDP"}:
        warnings.append(f"Under Incoterm {incoterm}, delivery responsibility is broader, but insurance responsibility should still be confirmed.")
        recommendations.append("Confirm who carries insurance during the main international leg and destination delivery.")

    else:
        warnings.append("Incoterm is missing, so insurance responsibility is not clear.")
        recommendations.append("Confirm Incoterm before deciding who purchases insurance.")

    if "hazardous" in cargo_categories:
        blockers.append("Hazardous cargo insurance requires specialist confirmation and carrier acceptance.")

    if estimated_value_usd is not None and estimated_value_usd >= 10000:
        reasons.append("Cargo value is high enough to justify formal insurance review.")

    if blockers:
        status = "blocked"
        insurance_recommendation = "specialist_review_required"
        summary = "Insurance advice found blockers that require specialist review."
    elif (
        risk_level in {"high", "critical"}
        or fragile_or_sensitive
        or (estimated_value_usd is not None and estimated_value_usd >= 10000)
    ):
        status = "review_required"
        insurance_recommendation = "strongly_recommended"
        summary = "Cargo insurance is strongly recommended before shipment booking."
    elif warnings:
        status = "review_required"
        insurance_recommendation = "recommended"
        summary = "Cargo insurance should be reviewed before shipment booking."
    else:
        status = "clear"
        insurance_recommendation = "optional_for_first_pass"
        summary = "No major insurance concern was detected for first-pass planning."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "insurance_recommendation": insurance_recommendation,
        "estimated_cargo_value_usd": estimated_value_usd,
        "incoterm": incoterm,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "cargo_categories": sorted(cargo_categories),
        "reasons": list(dict.fromkeys(_clean_text(item) for item in reasons)),
        "blockers": list(dict.fromkeys(_clean_text(item) for item in blockers)),
        "warnings": list(dict.fromkeys(_clean_text(item) for item in warnings)),
        "recommendations": list(dict.fromkeys(_clean_text(item) for item in recommendations)),
    }
