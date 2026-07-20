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
    return " ".join(str(value).split())


def _bullet_lines(items: list[Any], limit: int = 10) -> list[str]:
    lines: list[str] = []

    for item in items[:limit]:
        text = _clean_text(item)

        if text:
            lines.append(f"- {text}")

    return lines


def _metric_lines(metrics: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    for key, value in metrics.items():
        if value is None:
            continue

        lines.append(f"- **{key}**: {value}")

    return lines


def build_demo_report(payload: dict[str, Any]) -> str:
    executive_summary = _get_dict(payload.get("executive_summary"))
    shipment_snapshot = _get_dict(executive_summary.get("shipment_snapshot"))
    booking_readiness = _get_dict(payload.get("booking_readiness"))
    final_answer = _get_dict(payload.get("final_answer"))
    action_plan = _get_dict(payload.get("action_plan"))
    ui_sections = _as_list(payload.get("ui_sections"))

    lines: list[str] = []

    lines.append("# Logistics Agent Demo Report")
    lines.append("")
    lines.append("## Executive Decision")
    lines.append("")
    lines.append(_clean_text(executive_summary.get("headline") or payload.get("short_answer") or "No executive summary available."))
    lines.append("")

    lines.extend(
        _metric_lines(
            {
                "decision": executive_summary.get("decision") or payload.get("decision"),
                "status": executive_summary.get("status") or payload.get("status"),
                "ready_for_first_pass": executive_summary.get("ready_for_first_pass"),
                "ready_for_booking": executive_summary.get("ready_for_booking"),
                "booking_score": executive_summary.get("booking_score"),
                "next_gate": executive_summary.get("next_gate"),
                "partner_review_status": payload.get("partner_review_status"),
            }
        )
    )

    lines.append("")
    lines.append("## Shipment Snapshot")
    lines.append("")
    lines.extend(_metric_lines(shipment_snapshot))

    lines.append("")
    lines.append("## Top Strengths")
    lines.append("")
    strengths = _bullet_lines(_as_list(executive_summary.get("top_strengths")))
    lines.extend(strengths or ["- No strengths listed."])

    lines.append("")
    lines.append("## Top Risks")
    lines.append("")
    risks = _bullet_lines(_as_list(executive_summary.get("top_risks")))
    lines.extend(risks or ["- No major risks listed."])

    lines.append("")
    lines.append("## Missing Items")
    lines.append("")
    missing_items = _bullet_lines(_as_list(executive_summary.get("top_missing_items")))
    lines.extend(missing_items or ["- No missing items listed."])

    lines.append("")
    lines.append("## Next Actions")
    lines.append("")
    next_actions = _bullet_lines(_as_list(executive_summary.get("top_next_actions")))
    lines.extend(next_actions or ["- No next actions listed."])

    lines.append("")
    lines.append("## Booking Readiness")
    lines.append("")
    lines.append(_clean_text(booking_readiness.get("summary") or "No booking readiness summary available."))
    lines.append("")
    lines.extend(
        _metric_lines(
            {
                "status": booking_readiness.get("status"),
                "ready_for_first_pass": booking_readiness.get("ready_for_first_pass"),
                "ready_for_booking": booking_readiness.get("ready_for_booking"),
                "score": booking_readiness.get("score"),
                "next_gate": booking_readiness.get("next_gate"),
            }
        )
    )

    lines.append("")
    lines.append("## Final Answer")
    lines.append("")
    lines.append(_clean_text(final_answer.get("answer_text") or "No final answer available."))

    lines.append("")
    lines.append("## Action Plan")
    lines.append("")
    lines.append("### Before Booking")
    lines.extend(_bullet_lines(_as_list(action_plan.get("before_booking")), limit=12) or ["- No before-booking actions listed."])

    lines.append("")
    lines.append("### Partner Steps")
    lines.extend(_bullet_lines(_as_list(action_plan.get("partner_steps")), limit=12) or ["- No partner steps listed."])

    lines.append("")
    lines.append("### User Questions")
    lines.extend(_bullet_lines(_as_list(action_plan.get("user_questions")), limit=12) or ["- No user questions listed."])

    lines.append("")
    lines.append("## UI Sections")
    lines.append("")

    for section in ui_sections:
        if not isinstance(section, dict):
            continue

        lines.append(f"### {_clean_text(section.get('title') or section.get('section_id') or 'Untitled Section')}")
        lines.append("")
        lines.append(f"**Status:** {_clean_text(section.get('status') or 'unknown')}")
        lines.append("")
        lines.append(_clean_text(section.get("summary") or "No summary available."))
        lines.append("")

        bullets = _bullet_lines(_as_list(section.get("bullets")), limit=5)
        actions = _bullet_lines(_as_list(section.get("actions")), limit=5)

        if bullets:
            lines.append("**Highlights:**")
            lines.extend(bullets)
            lines.append("")

        if actions:
            lines.append("**Actions:**")
            lines.extend(actions)
            lines.append("")

    lines.append("## Backend Validation")
    lines.append("")
    backend_validation = _get_dict(payload.get("backend_validation"))
    lines.extend(
        _metric_lines(
            {
                "response_contract_valid": backend_validation.get("response_contract_valid"),
                "response_contract_errors": backend_validation.get("response_contract_errors"),
                "response_contract_warnings": backend_validation.get("response_contract_warnings"),
            }
        )
    )

    lines.append("")

    return "\n".join(lines)
