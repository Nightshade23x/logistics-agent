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


# READY_TO_BOOK_GATE_V91
# Separate true booking requirements from review-only, informational, and
# document-pack follow-up items. The original lists remain in the payload for
# transparency; these helpers decide only which items control the booking gate.
_INFORMATIONAL_REVIEW_MARKERS = (
    "no known free trade agreement",
    "no free trade agreement",
    "no known fta",
    "gemini",
    "deterministic fallback",
    "review was not applicable",
    "checks are not connected yet",
)

_CRITICAL_REVIEW_MARKERS = (
    "hs code",
    "hazard",
    "dangerous goods",
    "radioactive",
    "sanction",
    "prohibited",
    "restricted",
    "specialist review required",
    "export control",
    "import restriction",
)

_DOCUMENT_FOLLOWUP_MARKERS = (
    "commercial invoice",
    "packing list",
    "bill of lading",
    "airway bill",
    "air waybill",
)

_SOFT_COST_BLOCKER_MARKERS = (
    "procurement value",
    "declared value",
    "landed cost inputs are incomplete",
    "landed_cost has blockers",
    "estimated cargo value is missing",
    "insurance advice is incomplete",
)

_GENERIC_MISSING_MESSAGES = {
    "landed_cost needs more information.",
    "document_requirements needs more information.",
    "trade_compliance needs more information.",
    "insurance needs more information.",
    "trade_terms needs more information.",
}


def _gate_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _is_cost_workflow(payload: dict[str, Any]) -> bool:
    intent = _gate_text(payload.get("detected_intent"))
    if intent in {"finance", "landed cost", "landed cost calculation", "cost"}:
        return True

    metadata = payload.get("request_metadata")
    source = metadata.get("input_source") if isinstance(metadata, dict) else None
    return "landed cost" in _gate_text(source)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    # V91_REPAIR_NORMALIZED_MARKERS
    # _gate_text() normalizes underscores/spaces in payload messages, so
    # normalize the marker side too before comparing. Without this,
    # "landed_cost has blockers" fails to match "landed cost has blockers"
    # and is incorrectly treated as a hard blocker.
    return any(_gate_text(marker) in text for marker in markers)


def _classify_booking_gate(
    payload: dict[str, Any],
    blockers: list[str],
    missing_information: list[str],
    review_items: list[str],
) -> dict[str, list[str]]:
    cost_workflow = _is_cost_workflow(payload)

    hard_blockers: list[str] = []
    booking_missing: list[str] = []
    booking_review: list[str] = []
    informational: list[str] = []
    pre_dispatch: list[str] = []

    def add_unique(target: list[str], value: str) -> None:
        cleaned = _clean_text(value)
        if cleaned and cleaned not in target:
            target.append(cleaned)

    # Existing blockers remain authoritative unless they are cost/value
    # completeness messages. Those are required data, not safety blockers.
    for item in blockers:
        normalized = _gate_text(item)

        if _contains_any(normalized, _SOFT_COST_BLOCKER_MARKERS):
            if "procurement value" in normalized or "declared value" in normalized:
                add_unique(booking_missing, item)
            elif cost_workflow:
                add_unique(booking_missing, item)
            else:
                add_unique(informational, item)
            continue

        add_unique(hard_blockers, item)

    for item in missing_information:
        normalized = _gate_text(item)

        if normalized in {_gate_text(value) for value in _GENERIC_MISSING_MESSAGES}:
            add_unique(informational, item)
            continue

        if normalized.startswith("document:") or _contains_any(
            normalized, _DOCUMENT_FOLLOWUP_MARKERS
        ):
            add_unique(pre_dispatch, item)
            continue

        is_cost_item = (
            normalized.startswith("landed cost input:")
            or any(
                token in normalized
                for token in (
                    "procurement value",
                    "declared value",
                    "freight quote",
                    "insurance premium",
                    "duty rate",
                    "import tax",
                    "vat rate",
                    "customs brokerage",
                    "local delivery",
                )
            )
        )

        if is_cost_item:
            if "procurement value" in normalized or "declared value" in normalized:
                add_unique(booking_missing, item)
            elif cost_workflow:
                add_unique(booking_missing, item)
            else:
                add_unique(informational, item)
            continue

        add_unique(booking_missing, item)

    for item in review_items:
        normalized = _gate_text(item)

        if _contains_any(normalized, _INFORMATIONAL_REVIEW_MARKERS):
            add_unique(informational, item)
            continue

        if _contains_any(normalized, _CRITICAL_REVIEW_MARKERS):
            add_unique(booking_review, item)
            continue

        # Ordinary review warnings stay visible but do not by themselves block
        # the "Ready to book" gate.
        add_unique(informational, item)

    booking_requirements: list[str] = []
    for item in hard_blockers + booking_missing + booking_review:
        add_unique(booking_requirements, item)

    return {
        "hard_blockers": hard_blockers,
        "booking_missing": booking_missing,
        "booking_review": booking_review,
        "booking_requirements": booking_requirements,
        "informational": informational,
        "pre_dispatch": pre_dispatch,
    }


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

    gate = _classify_booking_gate(
        payload,
        unique_blockers,
        unique_missing_information,
        unique_review_items,
    )
    hard_blockers = gate["hard_blockers"]
    booking_missing = gate["booking_missing"]
    booking_review = gate["booking_review"]
    booking_requirements = gate["booking_requirements"]
    informational_items = gate["informational"]
    pre_dispatch_items = gate["pre_dispatch"]

    if hard_blockers:
        status = "blocked"
        ready_for_booking = False
        ready_for_first_pass = False
        next_gate = "resolve_blockers"
        summary = "Shipment is not ready because safety, compliance, or validation blockers must be resolved."
    elif booking_missing:
        status = "needs_more_information"
        ready_for_booking = False
        ready_for_first_pass = True
        next_gate = "fill_booking_requirements"
        summary = "Shipment is ready for review, but required booking information is still missing."
    elif booking_review:
        status = "review_required"
        ready_for_booking = False
        ready_for_first_pass = True
        next_gate = "confirm_booking_review"
        summary = "Shipment is ready for review, but a booking-critical specialist check still needs confirmation."
    else:
        status = "ready_for_booking_review"
        ready_for_booking = True
        ready_for_first_pass = True
        next_gate = "booking_review"
        summary = "Shipment has the required information and checks to proceed to booking review."

    if ready_for_booking:
        score = max(score, 80)
    elif ready_for_first_pass and not hard_blockers:
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
        "booking_requirements": booking_requirements[:10],
        "booking_missing_items": booking_missing[:10],
        "booking_review_items": booking_review[:10],
        "hard_blockers": hard_blockers[:10],
        "informational_items": informational_items[:10],
        "pre_dispatch_items": pre_dispatch_items[:10],
        "ready_items": unique_ready_items[:10],
        "next_steps": unique_next_steps[:8],
    }
