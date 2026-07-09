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


def build_compact_frontend_payload(full_payload: dict[str, Any]) -> dict[str, Any]:
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
