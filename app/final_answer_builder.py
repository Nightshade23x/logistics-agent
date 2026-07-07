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
        "'with": "' with",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _collect_review_items(review: dict[str, Any], key: str) -> list[str]:
    if not isinstance(review, dict):
        return []

    items: list[str] = []

    for item in _as_list(review.get(key)):
        item_text = _clean_text(item)

        if item_text:
            items.append(item_text)

    return items


def build_final_answer(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("decision") or payload.get("status") or "review_required"
    detected_intent = payload.get("detected_intent") or "unknown"
    agents_called = payload.get("agents_called", [])

    if not isinstance(agents_called, list):
        agents_called = []

    logistics_metrics = payload.get("logistics_metrics", {})
    if not isinstance(logistics_metrics, dict):
        logistics_metrics = {}

    shopping_review = payload.get("shopping_quality_review", {})
    logistics_review = payload.get("logistics_quality_review", {})
    document_review = payload.get("document_quality_review", {})

    if not isinstance(shopping_review, dict):
        shopping_review = {}

    if not isinstance(logistics_review, dict):
        logistics_review = {}

    if not isinstance(document_review, dict):
        document_review = {}

    partner_review_status = payload.get("partner_review_status")

    blockers: list[str] = []
    warnings: list[str] = []
    ready_items: list[str] = []
    next_actions: list[str] = []

    review_sections = [
        ("Shopping", shopping_review),
        ("Logistics", logistics_review),
        ("Document", document_review),
    ]

    if partner_review_status in {
        "partner_review_not_configured",
        "not_configured",
        "not_implemented",
    }:
        warnings.append(
            "Partner Risk, Compliance, Trader, and Finance checks are not connected yet."
        )
        next_actions.append(
            "Connect partner services before treating the decision as final."
        )

    elif partner_review_status == "needs_more_information":
        warnings.append("Partner review needs more shipment or trade information.")
        next_actions.append(
            "Answer the clarification questions before partner review is rerun."
        )

    for review_name, review in review_sections:
        if not review.get("applicable"):
            continue

        review_status = review.get("status")

        if review_status == "clear":
            ready_items.append(f"{review_name} review is clear.")
        elif review_status == "review_required":
            warnings.append(f"{review_name} review requires checking.")
        elif review_status == "blocked":
            blockers.append(f"{review_name} review has blockers.")

        blockers.extend(_collect_review_items(review, "blockers"))
        warnings.extend(_collect_review_items(review, "warnings"))
        next_actions.extend(_collect_review_items(review, "recommendations"))

    clarification_questions = [
        _clean_text(question)
        for question in _as_list(payload.get("clarification_questions"))
        if _clean_text(question)
    ]

    if clarification_questions:
        next_actions.append("Answer the clarification questions shown in the payload.")

    total_cbm = logistics_metrics.get("total_cbm")
    total_weight_kg = logistics_metrics.get("total_weight_kg")
    recommended_container = logistics_metrics.get("recommended_container")

    metric_parts: list[str] = []

    if total_cbm is not None:
        metric_parts.append(f"{total_cbm} CBM")

    if total_weight_kg is not None:
        metric_parts.append(f"{total_weight_kg} kg")

    if recommended_container:
        metric_parts.append(f"recommended container: {recommended_container}")

    logistics_line = ""

    if metric_parts:
        logistics_line = (
            " Logistics summary: "
            + ", ".join(str(part) for part in metric_parts)
            + "."
        )

    if decision == "blocked" or blockers:
        headline = "Do not proceed yet. The request has blockers that must be resolved."
        final_status = "blocked"
    elif decision == "clear":
        headline = "This request is clear for first-pass planning."
        final_status = "clear"
    else:
        headline = (
            "This request is usable for first-pass planning, "
            "but review is still required."
        )
        final_status = "review_required"

    agents_text = ", ".join(str(agent) for agent in agents_called) if agents_called else "none"

    answer_text = (
        f"{headline} "
        f"Intent: {detected_intent}. "
        f"Agents used: {agents_text}."
        f"{logistics_line}"
    )

    unique_blockers = list(dict.fromkeys(blockers))
    unique_warnings = list(dict.fromkeys(warnings))
    unique_ready_items = list(dict.fromkeys(ready_items))
    unique_next_actions = list(dict.fromkeys(next_actions))

    return {
        "status": final_status,
        "headline": headline,
        "answer_text": _clean_text(answer_text),
        "ready_items": unique_ready_items[:6],
        "blockers": unique_blockers[:8],
        "warnings": unique_warnings[:8],
        "next_actions": unique_next_actions[:8],
    }
