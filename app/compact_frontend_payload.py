from __future__ import annotations

from typing import Any


def _get_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _build_compact_frontend_payload_base(full_payload: dict[str, Any]) -> dict[str, Any]:
    executive_summary = _get_dict(full_payload.get("executive_summary"))
    booking_readiness = _get_dict(full_payload.get("booking_readiness"))
    final_answer = _get_dict(full_payload.get("final_answer"))
    action_plan = _get_dict(full_payload.get("action_plan"))
    logistics_metrics = _get_dict(full_payload.get("logistics_metrics"))
    logistics_visualizer = _get_dict(full_payload.get("logistics_visualizer"))
    backend_validation = _get_dict(full_payload.get("backend_validation"))
    request_metadata = _get_dict(full_payload.get("request_metadata"))

    return {
        "payload_type": "compact_frontend_payload",
        "agent_name": full_payload.get("agent_name"),
        "status": full_payload.get("status"),
        "decision": full_payload.get("decision"),
        "detected_intent": full_payload.get("detected_intent"),
        "agents_called": _as_list(full_payload.get("agents_called")),
        "short_answer": full_payload.get("short_answer"),
        "executive_summary": executive_summary,
        "ui_sections": _as_list(full_payload.get("ui_sections")),
        "booking_readiness": booking_readiness,
        "final_answer": final_answer,
        "action_plan": action_plan,
        "logistics_metrics": logistics_metrics,
        "logistics_visualizer": logistics_visualizer,
        "partner_review_status": full_payload.get("partner_review_status"),
        "partner_review_summary": full_payload.get("partner_review_summary"),
        "backend_validation": backend_validation,
        "request_metadata": request_metadata,
        "debug_counts": {
            "ui_sections_count": len(_as_list(full_payload.get("ui_sections"))),
            "missing_information_count": full_payload.get("missing_information_count"),
            "assumptions_count": full_payload.get("assumptions_count"),
            "booking_missing_count": len(_as_list(booking_readiness.get("missing_information"))),
            "booking_review_items_count": len(_as_list(booking_readiness.get("review_items"))),
            "visualizer_available": bool(logistics_visualizer),
        },
    }


# FRONTEND_BACKEND_FIELD_PASSTHROUGH_PATCH
def build_compact_frontend_payload(full_payload):
    """Build compact payload, then preserve newer backend fields for the UI.

    The backend now returns richer routing, partner-review, and specialist fields.
    The older compact frontend adapter should not drop those fields.
    """
    compact = _build_compact_frontend_payload_base(full_payload)

    if not isinstance(compact, dict) or not isinstance(full_payload, dict):
        return compact

    passthrough_keys = [
        "status",
        "summary",
        "detected_intent",
        "agents_called",
        "review_services_called",
        "partner_review",
        "partner_review_status",
        "partner_review_mode",
        "partner_review_attempted",
        "partner_review_service_called",
        "live_orchestrator_configured",
        "partner_review_attempted",
        "partner_review_service_called",
        "live_orchestrator_configured",
        "partner_review_payload",
        "partner_agent_errors",
        "specialist_responses",
        "specialist_statuses",
        "handoff_payload",
        "handoff_requests",
        "final_answer",
        "final_verdict",
        "router_source",
        "trained_router_decision",
        "logistics_input",
        "trader_input",
        "missing_information",
    ]

    for key in passthrough_keys:
        value = full_payload.get(key)
        if value is not None:
            compact[key] = value

    partner_review = full_payload.get("partner_review")
    if isinstance(partner_review, dict):
        compact["partner_review"] = partner_review

        if compact.get("partner_review_status") is None and partner_review.get("status") is not None:
            compact["partner_review_status"] = partner_review.get("status")

        if compact.get("partner_review_summary") is None and partner_review.get("summary") is not None:
            compact["partner_review_summary"] = partner_review.get("summary")

        partner_handoff = partner_review.get("handoff_payload")
        if compact.get("partner_review_payload") is None and isinstance(partner_handoff, dict):
            compact["partner_review_payload"] = partner_handoff

    if not compact.get("specialist_statuses"):
        specialist_statuses = {}

        specialist_responses = compact.get("specialist_responses")
        if isinstance(specialist_responses, dict):
            for agent_name, response in specialist_responses.items():
                if isinstance(response, dict) and response.get("status") is not None:
                    specialist_statuses[agent_name] = response.get("status")

        if compact.get("partner_review_status") is not None:
            specialist_statuses.setdefault("partner_review_service", compact.get("partner_review_status"))

        if specialist_statuses:
            compact["specialist_statuses"] = specialist_statuses

    return compact

