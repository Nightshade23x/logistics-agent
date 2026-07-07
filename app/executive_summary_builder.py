from __future__ import annotations

from typing import Any


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
        "likelytoo": "likely too",
        "aquote": "a quote",
        "neededfor": "needed for",
        "especiallyfor": "especially for",
        "modebefore": "mode before",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _get_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in {None, ""}:
            return value

    return None


def _unique_clean(items: list[Any], limit: int) -> list[str]:
    cleaned: list[str] = []

    for item in items:
        text = _clean_text(item)

        if text and text not in cleaned:
            cleaned.append(text)

    return cleaned[:limit]


def _collect_top_risks(payload: dict[str, Any]) -> list[str]:
    risks: list[Any] = []

    final_answer = _get_dict(payload.get("final_answer"))
    booking_readiness = _get_dict(payload.get("booking_readiness"))
    logistics_review = _get_dict(payload.get("logistics_quality_review"))
    insurance_advice = _get_dict(payload.get("insurance_advice"))
    trade_compliance = _get_dict(payload.get("trade_compliance_readiness"))
    landed_cost = _get_dict(payload.get("landed_cost_advice"))

    risks.extend(_as_list(final_answer.get("warnings")))
    risks.extend(_as_list(booking_readiness.get("review_items")))
    risks.extend(_as_list(logistics_review.get("warnings")))
    risks.extend(_as_list(insurance_advice.get("warnings")))
    risks.extend(_as_list(trade_compliance.get("warnings")))
    risks.extend(_as_list(trade_compliance.get("compliance_flags")))
    risks.extend(_as_list(landed_cost.get("warnings")))

    partner_review_status = payload.get("partner_review_status")
    if partner_review_status in {"partner_review_not_configured", "not_configured", "not_implemented"}:
        risks.insert(0, "Partner Risk, Compliance, Trader, and Finance checks are not connected yet.")

    return _unique_clean(risks, limit=8)


def _collect_missing_items(payload: dict[str, Any]) -> list[str]:
    missing: list[Any] = []

    booking_readiness = _get_dict(payload.get("booking_readiness"))
    landed_cost = _get_dict(payload.get("landed_cost_advice"))
    trade_compliance = _get_dict(payload.get("trade_compliance_readiness"))
    document_requirements = _get_dict(payload.get("document_requirements_advice"))
    trade_terms = _get_dict(payload.get("trade_terms_advice"))

    missing.extend(_as_list(booking_readiness.get("missing_information")))
    missing.extend(_as_list(landed_cost.get("missing_cost_inputs")))
    missing.extend(_as_list(trade_compliance.get("missing_information")))
    missing.extend(_as_list(document_requirements.get("missing_or_unconfirmed_documents")))
    missing.extend(_as_list(trade_terms.get("user_questions")))
    missing.extend(_as_list(payload.get("clarification_questions")))

    return _unique_clean(missing, limit=10)


def _collect_next_actions(payload: dict[str, Any]) -> list[str]:
    actions: list[Any] = []

    action_plan = _get_dict(payload.get("action_plan"))
    booking_readiness = _get_dict(payload.get("booking_readiness"))
    final_answer = _get_dict(payload.get("final_answer"))

    actions.extend(_as_list(action_plan.get("immediate_actions")))
    actions.extend(_as_list(action_plan.get("partner_steps")))
    actions.extend(_as_list(action_plan.get("before_booking")))
    actions.extend(_as_list(booking_readiness.get("next_steps")))
    actions.extend(_as_list(final_answer.get("next_actions")))

    return _unique_clean(actions, limit=10)


def _collect_strengths(payload: dict[str, Any]) -> list[str]:
    strengths: list[Any] = []

    booking_readiness = _get_dict(payload.get("booking_readiness"))
    final_answer = _get_dict(payload.get("final_answer"))
    procurement_advice = _get_dict(payload.get("procurement_advice"))
    shopping_review = _get_dict(payload.get("shopping_quality_review"))

    strengths.extend(_as_list(booking_readiness.get("ready_items")))
    strengths.extend(_as_list(final_answer.get("ready_items")))

    if shopping_review.get("status") == "clear":
        strengths.append("Shopping selection is clear for first-pass planning.")

    if procurement_advice.get("status") == "clear":
        strengths.append("Procurement advice is clear for first-pass supplier planning.")

    return _unique_clean(strengths, limit=6)


def build_executive_summary(payload: dict[str, Any]) -> dict[str, Any]:
    booking_readiness = _get_dict(payload.get("booking_readiness"))
    logistics_metrics = _get_dict(payload.get("logistics_metrics"))
    procurement_advice = _get_dict(payload.get("procurement_advice"))
    trade_terms = _get_dict(payload.get("trade_terms_advice"))
    landed_cost = _get_dict(payload.get("landed_cost_advice"))
    trade_compliance = _get_dict(payload.get("trade_compliance_readiness"))

    status = _first_present(
        booking_readiness.get("status"),
        payload.get("decision"),
        payload.get("status"),
        "review_required",
    )

    ready_for_first_pass = bool(booking_readiness.get("ready_for_first_pass"))
    ready_for_booking = bool(booking_readiness.get("ready_for_booking"))

    if ready_for_booking:
        headline = "Shipment is ready for booking review."
    elif ready_for_first_pass:
        headline = "Shipment is usable for first-pass planning, but not ready to book yet."
    elif status == "blocked":
        headline = "Shipment is blocked until critical issues are resolved."
    else:
        headline = "Shipment needs more information before it can proceed."

    shipment_snapshot = {
        "intent": payload.get("detected_intent"),
        "agents_called": _as_list(payload.get("agents_called")),
        "estimated_procurement_cost_usd": procurement_advice.get("estimated_total_procurement_cost_usd"),
        "total_cbm": logistics_metrics.get("total_cbm"),
        "total_weight_kg": logistics_metrics.get("total_weight_kg"),
        "recommended_container": logistics_metrics.get("recommended_container"),
        "recommended_load_type": logistics_metrics.get("recommended_load_type"),
        "risk_level": logistics_metrics.get("risk_level"),
        "origin_country": _first_present(
            trade_terms.get("origin_country"),
            landed_cost.get("known_inputs", {}).get("origin_country") if isinstance(landed_cost.get("known_inputs"), dict) else None,
            trade_compliance.get("origin_country"),
        ),
        "destination_country": _first_present(
            trade_terms.get("destination_country"),
            landed_cost.get("known_inputs", {}).get("destination_country") if isinstance(landed_cost.get("known_inputs"), dict) else None,
            trade_compliance.get("destination_country"),
        ),
        "incoterm": trade_terms.get("incoterm"),
        "partner_review_status": payload.get("partner_review_status"),
    }

    return {
        "applicable": True,
        "status": status,
        "headline": headline,
        "decision": payload.get("decision"),
        "ready_for_first_pass": ready_for_first_pass,
        "ready_for_booking": ready_for_booking,
        "booking_score": booking_readiness.get("score"),
        "next_gate": booking_readiness.get("next_gate"),
        "shipment_snapshot": shipment_snapshot,
        "top_strengths": _collect_strengths(payload),
        "top_risks": _collect_top_risks(payload),
        "top_missing_items": _collect_missing_items(payload),
        "top_next_actions": _collect_next_actions(payload),
    }
