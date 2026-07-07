from __future__ import annotations

from typing import Any


KNOWN_INCOTERMS = {
    "EXW",
    "FCA",
    "FAS",
    "FOB",
    "CFR",
    "CIF",
    "CPT",
    "CIP",
    "DAP",
    "DPU",
    "DDP",
}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _clean_text(value: Any) -> str:
    return " ".join(str(value).split())


def _get_nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})

    if isinstance(value, dict):
        return value

    return {}


def _extract_possible_incoterm_from_text(text: str) -> str | None:
    words = text.upper().replace("-", " ").replace("_", " ").split()

    for word in words:
        cleaned = "".join(character for character in word if character.isalpha())

        if cleaned in KNOWN_INCOTERMS:
            return cleaned

    return None


def _collect_text_values(data: Any) -> list[str]:
    values: list[str] = []

    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, (dict, list)):
                values.extend(_collect_text_values(value))

    elif isinstance(data, list):
        for item in data:
            values.extend(_collect_text_values(item))

    return values


def _find_incoterm(
    user_agent_response: dict[str, Any],
    request_text: str | None = None,
) -> str | None:
    if request_text:
        possible = _extract_possible_incoterm_from_text(request_text)

        if possible:
            return possible

    direct_keys = [
        "incoterm",
        "trade_term",
        "trade_terms",
        "shipping_term",
        "shipping_terms",
    ]

    candidate_containers: list[dict[str, Any]] = [user_agent_response]

    specialist_responses = _get_nested_dict(user_agent_response, "specialist_responses")

    for agent_name in ["shopping_agent", "logistics_agent", "document_ai_agent"]:
        agent_response = specialist_responses.get(agent_name, {})

        if not isinstance(agent_response, dict):
            continue

        candidate_containers.append(agent_response)

        handoff_payload = agent_response.get("handoff_payload", {})
        if isinstance(handoff_payload, dict):
            candidate_containers.append(handoff_payload)

    for container in candidate_containers:
        for key in direct_keys:
            value = container.get(key)

            if value:
                possible = _extract_possible_incoterm_from_text(str(value))

                if possible:
                    return possible

    all_text = " ".join(_collect_text_values(user_agent_response))
    return _extract_possible_incoterm_from_text(all_text)


def _extract_origin_destination_from_text(request_text: str | None) -> tuple[str | None, str | None]:
    if not request_text:
        return None, None

    words = request_text.replace(",", " ").replace(".", " ").split()
    lowered_words = [word.lower() for word in words]

    if "from" not in lowered_words or "to" not in lowered_words:
        return None, None

    from_index = lowered_words.index("from")
    to_index = lowered_words.index("to")

    if from_index >= to_index:
        return None, None

    origin_words = words[from_index + 1:to_index]
    destination_words = words[to_index + 1:]

    stop_words = {
        "under", "with", "using", "terms", "term", "incoterm",
        "incoterms", "for", "and", "budget", "prefer", "avoid"
    }

    clean_origin = []
    for word in origin_words:
        if word.lower() in stop_words:
            break
        clean_origin.append(word)

    clean_destination = []
    for word in destination_words:
        if word.lower() in stop_words:
            break
        clean_destination.append(word)

    origin = " ".join(clean_origin).strip() or None
    destination = " ".join(clean_destination).strip() or None

    return origin, destination


def _find_origin_destination(
    user_agent_response: dict[str, Any],
    request_text: str | None = None,
) -> tuple[str | None, str | None]:
    origin, destination = _extract_origin_destination_from_text(request_text)

    specialist_responses = _get_nested_dict(user_agent_response, "specialist_responses")

    for agent_name in ["shopping_agent", "logistics_agent", "document_ai_agent", "partner_review_service"]:
        agent_response = specialist_responses.get(agent_name, {})

        if not isinstance(agent_response, dict):
            continue

        handoff_payload = agent_response.get("handoff_payload", {})
        if not isinstance(handoff_payload, dict):
            handoff_payload = {}

        for container in [agent_response, handoff_payload]:
            origin = (
                origin
                or container.get("origin_country")
                or container.get("origin")
                or container.get("supplier_country")
            )
            destination = (
                destination
                or container.get("destination_country")
                or container.get("destination")
                or container.get("ship_to_country")
            )

    partner_review = user_agent_response.get("partner_review", {})
    if isinstance(partner_review, dict):
        origin = origin or partner_review.get("origin_country")
        destination = destination or partner_review.get("destination_country")

    return (
        _clean_text(origin) if origin else None,
        _clean_text(destination) if destination else None,
    )


def build_trade_terms_advice(
    user_agent_response: dict[str, Any],
    request_text: str | None = None,
) -> dict[str, Any]:
    incoterm = _find_incoterm(user_agent_response, request_text=request_text)
    origin, destination = _find_origin_destination(
        user_agent_response,
        request_text=request_text,
    )

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    user_questions: list[str] = []

    if not incoterm:
        warnings.append("No Incoterm or shipping trade term was confirmed.")
        user_questions.append(
            "Which Incoterm should be used for this shipment: EXW, FOB, CIF, DAP, DDP, or another term?"
        )
        recommendations.append(
            "Confirm the Incoterm before final landed cost, insurance, customs responsibility, or booking decisions."
        )

    if not origin:
        warnings.append("Origin country is not fully confirmed for trade-term planning.")
        user_questions.append("What is the origin country or supplier country?")

    if not destination:
        warnings.append("Destination country is not fully confirmed for trade-term planning.")
        user_questions.append("What is the destination country?")

    responsibility_notes: list[str] = []

    if incoterm == "EXW":
        warnings.append(
            "EXW places most logistics responsibility on the buyer, including pickup and export-side coordination."
        )
        responsibility_notes.append("Buyer usually handles pickup, main freight, insurance, import clearance, and final delivery.")
        recommendations.append("Use EXW only if the buyer can manage origin pickup and export-side logistics.")

    elif incoterm in {"FOB", "FAS", "FCA"}:
        responsibility_notes.append("Seller handles origin-side delivery up to the agreed handover point.")
        responsibility_notes.append("Buyer usually handles main freight, insurance decision, import clearance, and destination delivery.")
        recommendations.append("Confirm the named port/place because FOB/FCA responsibility depends on the handover point.")

    elif incoterm in {"CFR", "CIF", "CPT", "CIP"}:
        responsibility_notes.append("Seller arranges main carriage, but risk transfer may occur earlier than final destination.")
        recommendations.append("Check risk transfer point carefully before assuming the seller covers all transit risk.")

        if incoterm in {"CIF", "CIP"}:
            responsibility_notes.append("Seller normally arranges minimum insurance cover.")
            recommendations.append("Check whether the insurance cover is sufficient for fragile or high-value cargo.")

    elif incoterm in {"DAP", "DPU"}:
        responsibility_notes.append("Seller usually handles transport to the named destination place.")
        responsibility_notes.append("Buyer usually handles import clearance and import taxes unless otherwise agreed.")
        recommendations.append("Confirm the named destination place and unloading responsibility.")

    elif incoterm == "DDP":
        warnings.append(
            "DDP gives the seller the highest responsibility, including import-side duties and taxes."
        )
        responsibility_notes.append("Seller usually handles transport, import clearance, duties, taxes, and delivery.")
        recommendations.append("Use DDP only if the seller can legally and operationally handle import clearance in the destination country.")

    if incoterm:
        status = "review_required" if warnings else "clear"
        summary = f"Trade terms advice prepared for Incoterm {incoterm}."
    else:
        status = "needs_more_information"
        summary = "Trade terms advice needs an Incoterm before final booking or landed-cost decisions."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "incoterm": incoterm,
        "origin_country": origin,
        "destination_country": destination,
        "responsibility_notes": list(dict.fromkeys(responsibility_notes)),
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "recommendations": list(dict.fromkeys(recommendations)),
        "user_questions": list(dict.fromkeys(user_questions)),
    }
