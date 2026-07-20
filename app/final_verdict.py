from __future__ import annotations

from typing import Any


BLOCKING_STATUSES = {
    "blocked",
}

REVIEW_STATUSES = {
    "critical_review_required",
    "review_required",
    "needs_more_information",
    "partial_plan_needs_more_information",
    "partner_review_not_configured",
    "not_configured",
    "not_implemented",
    "error",
}


def _collect_agent_statuses(response: dict[str, Any]) -> list[str]:
    statuses: list[str] = []

    if response.get("status"):
        statuses.append(str(response["status"]))

    specialist_responses = response.get("specialist_responses", {})

    for value in specialist_responses.values():
        if isinstance(value, dict) and value.get("status"):
            statuses.append(str(value["status"]))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("status"):
                    statuses.append(str(item["status"]))

    partner_review = response.get("partner_review")
    if isinstance(partner_review, dict) and partner_review.get("status"):
        statuses.append(str(partner_review["status"]))

    return statuses


def derive_final_verdict(response: dict[str, Any]) -> dict[str, Any]:
    statuses = _collect_agent_statuses(response)
    missing_information = response.get("missing_information", [])
    partner_review_status = response.get("partner_review_status")

    blockers: list[str] = []
    warnings: list[str] = []

    if any(status in BLOCKING_STATUSES for status in statuses):
        verdict = "blocked"
        blockers.append("At least one agent reported a blocking or critical status.")
    elif missing_information:
        verdict = "review_required"
        warnings.append("Some required shipment or review information is missing.")
    elif any(status in REVIEW_STATUSES for status in statuses):
        verdict = "review_required"
        warnings.append("At least one agent requires review or is not fully configured.")
    else:
        verdict = "clear"

    if partner_review_status in {"partner_review_not_configured", "needs_more_information"}:
        warnings.append("Partner Risk, Compliance, Trader, and Finance checks are not fully live yet.")

    return {
        "verdict": verdict,
        "agent_statuses": statuses,
        "blockers": blockers,
        "warnings": warnings,
        "missing_information_count": len(missing_information),
        "partner_review_status": partner_review_status,
    }


def format_final_verdict(verdict: dict[str, Any]) -> str:
    lines = [
        "FINAL VERDICT",
        "------------------------------",
        f"Decision: {verdict['verdict']}",
    ]

    if verdict.get("blockers"):
        lines.append("")
        lines.append("Blockers:")
        for blocker in verdict["blockers"]:
            lines.append(f"- {blocker}")

    if verdict.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        for warning in verdict["warnings"]:
            lines.append(f"- {warning}")

    return "\n".join(lines)
