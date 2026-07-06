from __future__ import annotations

from typing import Any


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def build_clarification_questions(response: dict[str, Any]) -> list[str]:
    questions: list[str] = []

    detected_intent = response.get("detected_intent")
    missing_information = response.get("missing_information", [])
    partner_review = response.get("partner_review", {})
    logistics_input = response.get("logistics_input", {})

    destination = (
        logistics_input.get("destination")
        or partner_review.get("destination_country")
        or response.get("destination_country")
    )

    origin = (
        logistics_input.get("origin")
        or partner_review.get("origin_country")
        or response.get("origin_country")
    )

    if not destination:
        questions.append("What is the destination country for this shipment?")

    if not origin:
        questions.append("What is the origin country or supplier country for this shipment?")

    for item in missing_information:
        item_text = str(item)

        if _contains_any(item_text, ["deadline", "transit time", "delivery"]):
            questions.append("What is the preferred delivery deadline or maximum acceptable transit time?")

        if _contains_any(item_text, ["port of loading", "port of discharge"]):
            questions.append("Which port of loading and port of discharge should be used?")

        if _contains_any(item_text, ["door-to-door", "port-to-port", "warehouse"]):
            questions.append("Do you need door-to-door, port-to-port, or warehouse-to-warehouse service?")

        if _contains_any(item_text, ["insurance"]):
            questions.append("Has cargo insurance already been arranged, or should it be included?")

        if _contains_any(item_text, ["estimated from catalog", "dimensions"]):
            questions.append("Can you confirm the final packed dimensions and weight for the catalog-estimated items?")

    if partner_review.get("status") == "needs_more_information":
        missing_required_fields = partner_review.get("missing_required_fields", [])

        for field in missing_required_fields:
            field_text = str(field).lower()

            if "destination" in field_text and not destination:
                questions.append("What is the destination country for this shipment?")

            elif "item" in field_text:
                questions.append("Which items should be included in the partner review?")

    unique_questions = []
    seen = set()

    for question in questions:
        if question not in seen:
            unique_questions.append(question)
            seen.add(question)

    return unique_questions[:6]
