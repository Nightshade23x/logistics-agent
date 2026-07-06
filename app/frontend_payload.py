from __future__ import annotations

from typing import Any


def _shorten(text: str | None, limit: int = 500) -> str:
    if not text:
        return ""

    cleaned = " ".join(str(text).split())

    if len(cleaned) <= limit:
        return cleaned

    return cleaned[:limit].rstrip() + "..."


def _extract_logistics_metrics(response: dict[str, Any]) -> dict[str, Any]:
    logistics_response = response.get("specialist_responses", {}).get("logistics_agent", {})

    if not isinstance(logistics_response, dict):
        return {}

    handoff_payload = logistics_response.get("handoff_payload", {})

    return {
        "total_cbm": handoff_payload.get("total_cbm"),
        "total_weight_kg": handoff_payload.get("total_weight_kg"),
        "recommended_container": handoff_payload.get("recommended_container"),
        "recommended_load_type": handoff_payload.get("recommended_load_type"),
        "risk_level": handoff_payload.get("risk_level"),
        "risk_score": handoff_payload.get("risk_score"),
        "readiness_status": handoff_payload.get("readiness_status"),
    }


def _extract_agent_summaries(response: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = []
    specialist_responses = response.get("specialist_responses", {})

    for agent_name, agent_response in specialist_responses.items():
        if not isinstance(agent_response, dict):
            continue

        summaries.append(
            {
                "agent_name": agent_name,
                "status": agent_response.get("status"),
                "summary": agent_response.get("summary"),
            }
        )

    return summaries


def build_frontend_payload(response: dict[str, Any]) -> dict[str, Any]:
    final_verdict = response.get("final_verdict", {})
    partner_review = response.get("partner_review", {})
    missing_information = response.get("missing_information", [])

    return {
        "agent_name": response.get("agent_name"),
        "status": response.get("status"),
        "detected_intent": response.get("detected_intent"),
        "agents_called": response.get("agents_called", []),
        "summary": response.get("summary"),
        "short_answer": _shorten(response.get("final_answer")),
        "final_verdict": final_verdict,
        "decision": final_verdict.get("verdict"),
        "logistics_metrics": _extract_logistics_metrics(response),
        "partner_review_status": partner_review.get("status"),
        "partner_review_summary": partner_review.get("summary"),
        "missing_information_count": len(missing_information),
        "missing_information_preview": missing_information[:5],
        "agent_summaries": _extract_agent_summaries(response),
        "raw_response": response,
    }
