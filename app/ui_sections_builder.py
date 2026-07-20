from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _get_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _clean_text(value: Any) -> str:
    text = str(value)

    replacements = {
        "Trader,and": "Trader, and",
        "DAP,DDP": "DAP, DDP",
        "20ftStandard": "20ft Standard",
        "beforebooking": "before booking",
        "reliableestimate": "reliable estimate",
        "calculatinglanded": "calculating landed",
        "transportdocument": "transport document",
        "beforetreating": "before treating",
        "reviewis": "review is",
        "wereestimated": "were estimated",
        "propertieswere": "properties were",
        "abovenon-stackable": "above non-stackable",
        "cushioning,strong": "cushioning, strong",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _unique_clean(items: list[Any], limit: int = 6) -> list[str]:
    cleaned: list[str] = []

    for item in items:
        text = _clean_text(item)

        if text and text not in cleaned:
            cleaned.append(text)

    return cleaned[:limit]


def _card(
    section_id: str,
    title: str,
    status: str | None,
    summary: str,
    metrics: dict[str, Any] | None = None,
    bullets: list[Any] | None = None,
    actions: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "title": title,
        "status": status or "unknown",
        "summary": _clean_text(summary),
        "metrics": metrics or {},
        "bullets": _unique_clean(bullets or [], limit=8),
        "actions": _unique_clean(actions or [], limit=8),
    }


def build_ui_sections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    executive_summary = _get_dict(payload.get("executive_summary"))
    shipment_snapshot = _get_dict(executive_summary.get("shipment_snapshot"))

    procurement_advice = _get_dict(payload.get("procurement_advice"))
    shopping_quality = _get_dict(payload.get("shopping_quality_review"))
    logistics_quality = _get_dict(payload.get("logistics_quality_review"))
    trade_compliance = _get_dict(payload.get("trade_compliance_readiness"))
    document_requirements = _get_dict(payload.get("document_requirements_advice"))
    landed_cost = _get_dict(payload.get("landed_cost_advice"))
    insurance_advice = _get_dict(payload.get("insurance_advice"))
    booking_readiness = _get_dict(payload.get("booking_readiness"))
    action_plan = _get_dict(payload.get("action_plan"))

    sections: list[dict[str, Any]] = []

    sections.append(
        _card(
            section_id="executive_decision",
            title="Executive Decision",
            status=executive_summary.get("status") or payload.get("decision"),
            summary=executive_summary.get("headline") or payload.get("short_answer") or "No executive summary available.",
            metrics={
                "decision": executive_summary.get("decision") or payload.get("decision"),
                "ready_for_first_pass": executive_summary.get("ready_for_first_pass"),
                "ready_for_booking": executive_summary.get("ready_for_booking"),
                "booking_score": executive_summary.get("booking_score"),
                "next_gate": executive_summary.get("next_gate"),
            },
            bullets=_as_list(executive_summary.get("top_risks")),
            actions=_as_list(executive_summary.get("top_next_actions")),
        )
    )

    sections.append(
        _card(
            section_id="shipment_snapshot",
            title="Shipment Snapshot",
            status=payload.get("status"),
            summary="Key shipment facts for first-pass planning.",
            metrics={
                "intent": shipment_snapshot.get("intent") or payload.get("detected_intent"),
                "estimated_procurement_cost_usd": shipment_snapshot.get("estimated_procurement_cost_usd"),
                "total_cbm": shipment_snapshot.get("total_cbm"),
                "total_weight_kg": shipment_snapshot.get("total_weight_kg"),
                "recommended_container": shipment_snapshot.get("recommended_container"),
                "recommended_load_type": shipment_snapshot.get("recommended_load_type"),
                "risk_level": shipment_snapshot.get("risk_level"),
                "origin_country": shipment_snapshot.get("origin_country"),
                "destination_country": shipment_snapshot.get("destination_country"),
                "incoterm": shipment_snapshot.get("incoterm"),
            },
            bullets=[
                f"Agents called: {', '.join(str(agent) for agent in _as_list(payload.get('agents_called')))}",
                f"Partner review status: {payload.get('partner_review_status')}",
            ],
        )
    )

    sections.append(
        _card(
            section_id="procurement",
            title="Procurement",
            status=procurement_advice.get("status") or shopping_quality.get("status"),
            summary=procurement_advice.get("summary") or shopping_quality.get("summary") or "No procurement advice available.",
            metrics={
                "selected_items_count": procurement_advice.get("selected_items_count") or shopping_quality.get("selected_items_count"),
                "supplier_options_count": procurement_advice.get("supplier_options_count"),
                "estimated_total_procurement_cost_usd": procurement_advice.get("estimated_total_procurement_cost_usd") or shopping_quality.get("estimated_total_procurement_cost_usd"),
                "budget_usd": procurement_advice.get("budget_usd") or shopping_quality.get("budget_usd"),
                "supplier_countries": procurement_advice.get("selected_supplier_countries") or shopping_quality.get("selected_supplier_countries"),
            },
            bullets=_as_list(procurement_advice.get("recommendations")) + _as_list(procurement_advice.get("negotiation_points")),
            actions=_as_list(procurement_advice.get("user_questions")),
        )
    )

    sections.append(
        _card(
            section_id="logistics",
            title="Logistics",
            status=logistics_quality.get("status"),
            summary=logistics_quality.get("summary") or "No logistics review available.",
            metrics={
                "total_cbm": logistics_quality.get("total_cbm"),
                "total_weight_kg": logistics_quality.get("total_weight_kg"),
                "recommended_container": logistics_quality.get("recommended_container"),
                "recommended_load_type": logistics_quality.get("recommended_load_type"),
                "risk_level": logistics_quality.get("risk_level"),
                "risk_score": logistics_quality.get("risk_score"),
                "readiness_status": logistics_quality.get("readiness_status"),
                "cargo_categories": logistics_quality.get("cargo_categories"),
            },
            bullets=_as_list(logistics_quality.get("warnings")),
            actions=_as_list(logistics_quality.get("recommendations")),
        )
    )

    sections.append(
        _card(
            section_id="compliance_documents",
            title="Compliance & Documents",
            status=trade_compliance.get("status") or document_requirements.get("status"),
            summary=trade_compliance.get("summary") or document_requirements.get("summary") or "No compliance/document review available.",
            metrics={
                "ready_for_partner_review": trade_compliance.get("ready_for_partner_review"),
                "origin_country": trade_compliance.get("origin_country") or document_requirements.get("origin_country"),
                "destination_country": trade_compliance.get("destination_country") or document_requirements.get("destination_country"),
                "incoterm": trade_compliance.get("incoterm") or document_requirements.get("incoterm"),
                "item_count": trade_compliance.get("item_count") or document_requirements.get("item_count"),
                "required_documents": document_requirements.get("required_documents"),
                "conditional_documents": document_requirements.get("conditional_documents"),
            },
            bullets=(
                _as_list(trade_compliance.get("missing_information"))
                + _as_list(trade_compliance.get("warnings"))
                + _as_list(trade_compliance.get("compliance_flags"))
                + _as_list(document_requirements.get("missing_or_unconfirmed_documents"))
            ),
            actions=_as_list(trade_compliance.get("recommendations")) + _as_list(document_requirements.get("recommendations")),
        )
    )

    sections.append(
        _card(
            section_id="costs_insurance",
            title="Costs & Insurance",
            status=landed_cost.get("status") or insurance_advice.get("status"),
            summary=landed_cost.get("summary") or insurance_advice.get("summary") or "No cost or insurance advice available.",
            metrics={
                "estimated_subtotal_known_usd": landed_cost.get("estimated_subtotal_known_usd"),
                "known_inputs": landed_cost.get("known_inputs"),
                "missing_cost_inputs": landed_cost.get("missing_cost_inputs"),
                "insurance_recommendation": insurance_advice.get("insurance_recommendation"),
                "estimated_cargo_value_usd": insurance_advice.get("estimated_cargo_value_usd"),
            },
            bullets=_as_list(landed_cost.get("warnings")) + _as_list(insurance_advice.get("warnings")),
            actions=_as_list(landed_cost.get("recommendations")) + _as_list(insurance_advice.get("recommendations")),
        )
    )

    sections.append(
        _card(
            section_id="partner_checks",
            title="Partner Checks",
            status=payload.get("partner_review_status"),
            summary=payload.get("partner_review_summary") or "Partner checks are not available yet.",
            metrics={
                "partner_review_status": payload.get("partner_review_status"),
            },
            bullets=[
                "Risk Agent, Compliance Agent, Trader Agent, and Finance Agent must be connected before final approval."
                if payload.get("partner_review_status") in {"partner_review_not_configured", "not_configured", "not_implemented"}
                else "Partner review is available."
            ],
            actions=_as_list(action_plan.get("partner_steps")),
        )
    )

    sections.append(
        _card(
            section_id="next_actions",
            title="Next Actions",
            status=action_plan.get("status") or booking_readiness.get("status"),
            summary=action_plan.get("summary") or booking_readiness.get("summary") or "No action plan available.",
            metrics={
                "booking_status": booking_readiness.get("status"),
                "ready_for_first_pass": booking_readiness.get("ready_for_first_pass"),
                "ready_for_booking": booking_readiness.get("ready_for_booking"),
                "next_gate": booking_readiness.get("next_gate"),
            },
            bullets=_as_list(booking_readiness.get("missing_information")) + _as_list(booking_readiness.get("review_items")),
            actions=(
                _as_list(action_plan.get("immediate_actions"))
                + _as_list(action_plan.get("before_booking"))
                + _as_list(action_plan.get("user_questions"))
                + _as_list(booking_readiness.get("next_steps"))
            ),
        )
    )

    return sections
