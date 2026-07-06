from __future__ import annotations

from typing import Any


def _clean_text(text: str | None) -> str:
    if not text:
        return ""

    cleaned = " ".join(str(text).split())

    replacements = {
        "kg.Recommended": "kg. Recommended",
        "supplieroption": "supplier option",
        "Risk,Compliance": "Risk, Compliance",
        "andFinance": "and Finance",
        "catalog item'": "catalog item '",
        "catalogitem": "catalog item",
        "item'": "item '",
    }

    for old_value, new_value in replacements.items():
        cleaned = cleaned.replace(old_value, new_value)

    return cleaned.strip()


def _shorten(text: str | None, limit: int = 500) -> str:
    cleaned = _clean_text(text)

    if len(cleaned) <= limit:
        return cleaned

    return cleaned[:limit].rstrip() + "..."


def _is_assumption_or_estimate(message: str) -> bool:
    lowered = message.lower()

    return any(
        marker in lowered
        for marker in [
            "estimated from catalog",
            "matched from catalog",
            "direct cbm was provided",
        ]
    )


def _build_short_answer(
    response: dict[str, Any],
    final_verdict: dict[str, Any],
    logistics_metrics: dict[str, Any],
    partner_review: dict[str, Any],
) -> str:
    decision = final_verdict.get("verdict", response.get("status"))
    agents_called = ", ".join(response.get("agents_called", []))

    parts = [
        f"Decision: {decision}.",
        f"Agents called: {agents_called}.",
    ]

    if logistics_metrics:
        parts.append(
            "Logistics: "
            f"{logistics_metrics.get('total_cbm')} CBM, "
            f"{logistics_metrics.get('total_weight_kg')} kg, "
            f"recommended container {logistics_metrics.get('recommended_container')}, "
            f"risk level {logistics_metrics.get('risk_level')}."
        )

    if partner_review:
        parts.append(
            "Partner review: "
            f"{partner_review.get('status')}."
        )

    return _clean_text(" ".join(parts))


def _split_missing_information(missing_information: list[Any]) -> tuple[list[str], list[str]]:
    real_missing = []
    assumptions = []

    for item in missing_information:
        cleaned_item = _clean_text(str(item))

        if _is_assumption_or_estimate(cleaned_item):
            assumptions.append(cleaned_item)
        else:
            real_missing.append(cleaned_item)

    return real_missing, assumptions


def _frontend_final_verdict(
    final_verdict: dict[str, Any],
    real_missing: list[str],
    assumptions: list[str],
) -> dict[str, Any]:
    frontend_verdict = dict(final_verdict)
    frontend_verdict["missing_information_count"] = len(real_missing)
    frontend_verdict["assumptions_count"] = len(assumptions)
    return frontend_verdict




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
                "summary": _clean_text(agent_response.get("summary")),
            }
        )

    return summaries


def build_frontend_payload(response: dict[str, Any], include_raw_response: bool = False) -> dict[str, Any]:
    final_verdict = response.get("final_verdict", {})
    partner_review = response.get("partner_review", {})
    missing_information = response.get("missing_information", [])
    real_missing, assumptions = _split_missing_information(missing_information)

    payload = {
        "agent_name": response.get("agent_name"),
        "status": response.get("status"),
        "detected_intent": response.get("detected_intent"),
        "agents_called": response.get("agents_called", []),
        "summary": response.get("summary"),
        "short_answer": _build_short_answer(
            response=response,
            final_verdict=final_verdict,
            logistics_metrics=_extract_logistics_metrics(response),
            partner_review=partner_review,
        ),
        "final_verdict": _frontend_final_verdict(
            final_verdict=final_verdict,
            real_missing=real_missing,
            assumptions=assumptions,
        ),
        "decision": final_verdict.get("verdict"),
        "logistics_metrics": _extract_logistics_metrics(response),
        "partner_review_status": partner_review.get("status"),
        "partner_review_summary": partner_review.get("summary"),
        "missing_information_count": len(real_missing),
        "missing_information_preview": real_missing[:5],
        "assumptions_count": len(assumptions),
        "assumptions_preview": assumptions[:5],
        "agent_summaries": _extract_agent_summaries(response),
    }

    if include_raw_response:
        payload["raw_response"] = response

    return payload
