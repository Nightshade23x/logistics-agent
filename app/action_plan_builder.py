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
        "item '": "item '",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _unique_clean(values: list[Any]) -> list[str]:
    cleaned: list[str] = []

    for value in values:
        text = _clean_text(value)

        if text:
            cleaned.append(text)

    return list(dict.fromkeys(cleaned))


def _get_review(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})

    if isinstance(value, dict):
        return value

    return {}


def _extend_from_review(
    review: dict[str, Any],
    immediate_actions: list[str],
    before_booking: list[str],
) -> None:
    blockers = _as_list(review.get("blockers"))
    warnings = _as_list(review.get("warnings"))
    recommendations = _as_list(review.get("recommendations"))

    for blocker in blockers:
        immediate_actions.append(blocker)

    for warning in warnings:
        before_booking.append(warning)

    for recommendation in recommendations:
        before_booking.append(recommendation)


def build_action_plan(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("decision") or payload.get("status") or "review_required"
    partner_review_status = payload.get("partner_review_status")

    shopping_review = _get_review(payload, "shopping_quality_review")
    logistics_review = _get_review(payload, "logistics_quality_review")
    document_review = _get_review(payload, "document_quality_review")
    trade_terms_advice = _get_review(payload, "trade_terms_advice")
    insurance_advice = _get_review(payload, "insurance_advice")
    document_requirements_advice = _get_review(payload, "document_requirements_advice")
    landed_cost_advice = _get_review(payload, "landed_cost_advice")
    final_answer = _get_review(payload, "final_answer")

    immediate_actions: list[str] = []
    before_booking: list[str] = []
    partner_steps: list[str] = []
    user_questions: list[str] = []
    ready_to_continue: list[str] = []

    for question in _as_list(payload.get("clarification_questions")):
        user_questions.append(question)

    for question in _as_list(trade_terms_advice.get("user_questions")):
        user_questions.append(question)

    for warning in _as_list(trade_terms_advice.get("warnings")):
        before_booking.append(warning)

    for recommendation in _as_list(trade_terms_advice.get("recommendations")):
        before_booking.append(recommendation)

    for warning in _as_list(insurance_advice.get("warnings")):
        before_booking.append(warning)

    for recommendation in _as_list(insurance_advice.get("recommendations")):
        before_booking.append(recommendation)

    for blocker in _as_list(insurance_advice.get("blockers")):
        immediate_actions.append(blocker)

    for missing_document in _as_list(document_requirements_advice.get("missing_or_unconfirmed_documents")):
        before_booking.append(f"Confirm document: {missing_document}")

    for warning in _as_list(document_requirements_advice.get("warnings")):
        before_booking.append(warning)

    for recommendation in _as_list(document_requirements_advice.get("recommendations")):
        before_booking.append(recommendation)

    for question in _as_list(document_requirements_advice.get("user_questions")):
        user_questions.append(question)

    for missing_input in _as_list(landed_cost_advice.get("missing_cost_inputs")):
        before_booking.append(f"Confirm landed cost input: {missing_input}")

    for blocker in _as_list(landed_cost_advice.get("blockers")):
        immediate_actions.append(blocker)

    for warning in _as_list(landed_cost_advice.get("warnings")):
        before_booking.append(warning)

    for recommendation in _as_list(landed_cost_advice.get("recommendations")):
        before_booking.append(recommendation)

    for item in _as_list(final_answer.get("blockers")):
        immediate_actions.append(item)

    for item in _as_list(final_answer.get("warnings")):
        item_text = _clean_text(item)

        if "partner" in item_text.lower():
            partner_steps.append(item_text)
        else:
            before_booking.append(item_text)

    for item in _as_list(final_answer.get("next_actions")):
        item_text = _clean_text(item)
        lowered = item_text.lower()

        if any(marker in lowered for marker in ["partner", "risk mcp", "compliance mcp", "trader mcp", "finance rest"]):
            partner_steps.append(item_text)
        else:
            before_booking.append(item_text)

    for review_name, review in [
        ("Shopping", shopping_review),
        ("Logistics", logistics_review),
        ("Document", document_review),
    ]:
        if not review.get("applicable"):
            continue

        review_status = review.get("status")

        if review_status == "clear":
            ready_to_continue.append(f"{review_name} review is clear.")

        elif review_status == "blocked":
            immediate_actions.append(f"Resolve {review_name.lower()} blockers before continuing.")

        elif review_status == "review_required":
            before_booking.append(f"Review {review_name.lower()} findings before final approval.")

        _extend_from_review(review, immediate_actions, before_booking)

    if partner_review_status in {
        "partner_review_not_configured",
        "not_configured",
        "not_implemented",
    }:
        partner_steps.append("Connect Risk MCP server.")
        partner_steps.append("Connect Compliance MCP server.")
        partner_steps.append("Connect Trader MCP server.")
        partner_steps.append("Connect Finance REST API.")
        partner_steps.append("Rerun partner review after live partner services are connected.")

    elif partner_review_status == "needs_more_information":
        partner_steps.append("Provide missing partner-review fields.")
        partner_steps.append("Rerun partner review after missing information is supplied.")

    elif partner_review_status in {"ready_for_review", "clear"}:
        ready_to_continue.append("Partner review is available for checking.")

    if decision == "blocked":
        priority = "resolve_blockers"
        summary = "Resolve blockers before continuing."
    elif immediate_actions:
        priority = "resolve_immediate_actions"
        summary = "Some issues should be resolved before the shipment can move forward."
    elif before_booking or user_questions or partner_steps:
        priority = "review_before_booking"
        summary = "The plan is usable for first-pass planning, but review is needed before booking."
    else:
        priority = "ready_for_first_pass"
        summary = "The plan is ready for first-pass review."

    return {
        "status": priority,
        "summary": summary,
        "immediate_actions": _unique_clean(immediate_actions)[:8],
        "before_booking": _unique_clean(before_booking)[:10],
        "partner_steps": _unique_clean(partner_steps)[:8],
        "user_questions": _unique_clean(user_questions)[:6],
        "ready_to_continue": _unique_clean(ready_to_continue)[:6],
    }
