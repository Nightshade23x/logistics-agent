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
        "were estimated": "were estimated",
        "properties were": "properties were",
        "above non-stackable": "above non-stackable",
        "cushioning, strong": "cushioning, strong",
        "forthis": "for this",
        "IncotermFOB": "Incoterm FOB",
        "'with": "' with",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _get_review(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})

    if isinstance(value, dict):
        return value

    return {}


def _collect_items(review: dict[str, Any], key: str) -> list[str]:
    return [
        _clean_text(item)
        for item in _as_list(review.get(key))
        if _clean_text(item)
    ]


def _review_status(review: dict[str, Any]) -> str | None:
    status = review.get("status")

    if status is None:
        return None

    return str(status).lower()


def build_booking_readiness(payload: dict[str, Any]) -> dict[str, Any]:
    review_sections = {
        "shopping": _get_review(payload, "shopping_quality_review"),
        "logistics": _get_review(payload, "logistics_quality_review"),
        "document_quality": _get_review(payload, "document_quality_review"),
        "trade_terms": _get_review(payload, "trade_terms_advice"),
        "insurance": _get_review(payload, "insurance_advice"),
        "document_requirements": _get_review(payload, "document_requirements_advice"),
        "landed_cost": _get_review(payload, "landed_cost_advice"),
        "trade_compliance": _get_review(payload, "trade_compliance_readiness"),
    }

    partner_review_status = payload.get("partner_review_status")
    clarification_questions = _as_list(payload.get("clarification_questions"))

    blockers: list[str] = []
    review_items: list[str] = []
    ready_items: list[str] = []
    missing_information: list[str] = []
    next_steps: list[str] = []

    score = 100

    for section_name, review in review_sections.items():
        if not review:
            continue

        if review.get("applicable") is False:
            if section_name in {"document_quality"}:
                continue

            review_items.append(f"{section_name} review was not applicable.")
            score -= 5
            continue

        status = _review_status(review)

        if status == "clear":
            ready_items.append(f"{section_name} is clear.")
        elif status == "blocked":
            blockers.append(f"{section_name} has blockers.")
            blockers.extend(_collect_items(review, "blockers"))
            score -= 35
        elif status in {"needs_more_information", "not_applicable"}:
            missing_information.append(f"{section_name} needs more information.")
            missing_information.extend(_collect_items(review, "missing_cost_inputs"))
            missing_information.extend(_collect_items(review, "missing_or_unconfirmed_documents"))
            missing_information.extend(_collect_items(review, "user_questions"))
            score -= 20
        elif status == "review_required":
            review_items.append(f"{section_name} requires review.")
            review_items.extend(_collect_items(review, "warnings"))
            score -= 12

        blockers.extend(_collect_items(review, "blockers"))

        if section_name == "landed_cost":
            for missing_input in _as_list(review.get("missing_cost_inputs")):
                missing_information.append(f"landed cost input: {missing_input}")

        if section_name == "document_requirements":
            for missing_doc in _as_list(review.get("missing_or_unconfirmed_documents")):
                missing_information.append(f"document: {missing_doc}")

    if partner_review_status in {
        "partner_review_not_configured",
        "not_configured",
        "not_implemented",
    }:
        review_items.append("Partner Risk, Compliance, Trader, and Finance checks are not connected yet.")
        next_steps.append("Connect partner services and rerun partner review.")
        score -= 15

    elif partner_review_status == "needs_more_information":
        missing_information.append("Partner review needs more shipment or trade information.")
        next_steps.append("Provide missing partner-review information and rerun partner review.")
        score -= 20

    elif partner_review_status in {"clear", "ready_for_review"}:
        ready_items.append("Partner review is available for checking.")

    for question in clarification_questions:
        missing_information.append(question)

    if missing_information:
        next_steps.append("Answer missing-information questions before booking.")

    if review_items:
        next_steps.append("Review warnings before booking.")

    if blockers:
        next_steps.append("Resolve blockers before continuing.")

    unique_blockers = list(dict.fromkeys(_clean_text(item) for item in blockers if _clean_text(item)))
    unique_review_items = list(dict.fromkeys(_clean_text(item) for item in review_items if _clean_text(item)))
    unique_missing_information = list(dict.fromkeys(_clean_text(item) for item in missing_information if _clean_text(item)))
    unique_ready_items = list(dict.fromkeys(_clean_text(item) for item in ready_items if _clean_text(item)))
    unique_next_steps = list(dict.fromkeys(_clean_text(item) for item in next_steps if _clean_text(item)))

    score = max(0, min(100, score))

    if unique_blockers:
        status = "blocked"
        ready_for_booking = False
        ready_for_first_pass = False
        next_gate = "resolve_blockers"
        summary = "Shipment is not ready because blockers must be resolved."
    elif unique_missing_information:
        status = "needs_more_information"
        ready_for_booking = False
        ready_for_first_pass = True
        next_gate = "fill_missing_information"
        summary = "Shipment is usable for first-pass planning but missing information prevents booking."
    elif unique_review_items:
        status = "review_required"
        ready_for_booking = False
        ready_for_first_pass = True
        next_gate = "human_review"
        summary = "Shipment is usable for first-pass planning but needs review before booking."
    else:
        status = "ready_for_booking_review"
        ready_for_booking = True
        ready_for_first_pass = True
        next_gate = "booking_review"
        summary = "Shipment has enough first-pass information for booking review."

    if ready_for_booking:
        score = max(score, 80)
    elif ready_for_first_pass and not unique_blockers:
        score = max(score, 40)

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "score": score,
        "ready_for_first_pass": ready_for_first_pass,
        "ready_for_booking": ready_for_booking,
        "next_gate": next_gate,
        "blockers": unique_blockers[:10],
        "missing_information": unique_missing_information[:10],
        "review_items": unique_review_items[:10],
        "ready_items": unique_ready_items[:10],
        "next_steps": unique_next_steps[:8],
    }
