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
        "forthis": "for this",
        "IncotermFOB": "Incoterm FOB",
        "likelytoo": "likely too",
        "aquote": "a quote",
        "neededfor": "needed for",
        "especiallyfor": "especially for",
        "modebefore": "mode before",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _get_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _get_specialist_response(
    user_agent_response: dict[str, Any],
    agent_name: str,
) -> dict[str, Any]:
    specialist_responses = _get_dict(user_agent_response.get("specialist_responses"))
    return _get_dict(specialist_responses.get(agent_name))


def _get_handoff_payload(agent_response: dict[str, Any]) -> dict[str, Any]:
    return _get_dict(agent_response.get("handoff_payload"))


def _extract_items(user_agent_response: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for agent_name in ["shopping_agent", "logistics_agent", "document_ai_agent"]:
        response = _get_specialist_response(user_agent_response, agent_name)
        handoff = _get_handoff_payload(response)

        for container in [response, handoff]:
            for key in ["selected_items", "items", "products", "shipment_items", "cargo_items"]:
                for item in _as_list(container.get(key)):
                    if isinstance(item, dict):
                        items.append(item)

    unique_items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        identity = repr(sorted(item.items()))

        if identity in seen:
            continue

        unique_items.append(item)
        seen.add(identity)

    return unique_items


def _item_name(item: dict[str, Any]) -> str:
    return _clean_text(
        item.get("product_name")
        or item.get("name")
        or item.get("item_name")
        or item.get("description")
        or "Unnamed item"
    )


def _item_hs_code(item: dict[str, Any]) -> str | None:
    for key in ["hs_code", "hscode", "hs", "tariff_code", "commodity_code"]:
        value = item.get(key)

        if value:
            return _clean_text(value)

    return None


def _extract_trade_context(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    trade_terms = _get_dict(user_agent_response.get("trade_terms_advice"))
    partner_review = _get_dict(user_agent_response.get("partner_review"))

    origin_country = (
        trade_terms.get("origin_country")
        or partner_review.get("origin_country")
        or user_agent_response.get("origin_country")
    )

    destination_country = (
        trade_terms.get("destination_country")
        or partner_review.get("destination_country")
        or user_agent_response.get("destination_country")
    )

    incoterm = (
        trade_terms.get("incoterm")
        or user_agent_response.get("incoterm")
    )

    return {
        "origin_country": _clean_text(origin_country) if origin_country else None,
        "destination_country": _clean_text(destination_country) if destination_country else None,
        "incoterm": _clean_text(incoterm).upper() if incoterm else None,
    }


def _extract_special_cases(user_agent_response: dict[str, Any]) -> set[str]:
    cases: set[str] = set()

    logistics_quality = _get_dict(user_agent_response.get("logistics_quality_review"))
    special_handling = _get_dict(logistics_quality.get("special_handling"))

    for case in _as_list(special_handling.get("detected_special_cases")):
        cases.add(str(case).lower())

    logistics_response = _get_specialist_response(user_agent_response, "logistics_agent")
    logistics_handoff = _get_handoff_payload(logistics_response)

    for category in _as_list(logistics_handoff.get("cargo_categories")):
        category_text = str(category).lower()

        if "hazard" in category_text:
            cases.add("hazardous_cargo")

        if "fragile" in category_text:
            cases.add("fragile_cargo")

        if "battery" in category_text:
            cases.add("battery_possible")

    return cases


def build_trade_compliance_readiness(
    user_agent_response: dict[str, Any],
) -> dict[str, Any]:
    items = _extract_items(user_agent_response)
    trade_context = _extract_trade_context(user_agent_response)
    special_cases = _extract_special_cases(user_agent_response)

    document_requirements = _get_dict(user_agent_response.get("document_requirements_advice"))
    partner_review_status = user_agent_response.get("partner_review_status")

    blockers: list[str] = []
    warnings: list[str] = []
    missing_information: list[str] = []
    recommendations: list[str] = []
    compliance_flags: list[str] = []
    ready_items: list[str] = []

    origin_country = trade_context["origin_country"]
    destination_country = trade_context["destination_country"]
    incoterm = trade_context["incoterm"]

    if origin_country:
        ready_items.append(f"Origin country is known: {origin_country}.")
    else:
        missing_information.append("origin_country")

    if destination_country:
        ready_items.append(f"Destination country is known: {destination_country}.")
    else:
        missing_information.append("destination_country")

    if incoterm:
        ready_items.append(f"Incoterm is known: {incoterm}.")
    else:
        warnings.append("Incoterm is missing, so trade responsibility and documentation responsibility are not final.")

    if not items:
        blockers.append("No shipment items were found for compliance review.")
    else:
        ready_items.append(f"{len(items)} shipment item(s) are available for compliance review.")

    missing_hs_items: list[str] = []

    for item in items:
        name = _item_name(item)

        if not _item_hs_code(item):
            missing_hs_items.append(name)

        item_text = " ".join(str(value).lower() for value in item.values())

        if "battery" in item_text or "scooter" in item_text or "e-bike" in item_text:
            compliance_flags.append(f"{name}: possible battery-related compliance check needed.")

        if "chemical" in item_text or "flammable" in item_text:
            compliance_flags.append(f"{name}: possible hazardous goods compliance check needed.")

        if "food" in item_text or "cosmetic" in item_text or "medical" in item_text:
            compliance_flags.append(f"{name}: regulated product category may need extra permits or certificates.")

    if missing_hs_items:
        missing_information.extend(f"HS code for {name}" for name in missing_hs_items)
        recommendations.append("Confirm HS codes before duty, tariff, restriction, or permit review.")

    if "battery_possible" in special_cases:
        compliance_flags.append("Battery cargo may require MSDS, UN38.3, battery declaration, and carrier acceptance.")
        recommendations.append("Confirm battery type, watt-hours, MSDS, UN38.3 status, and packing method before booking.")

    if "hazardous_cargo" in special_cases:
        blockers.append("Possible hazardous cargo requires specialist compliance and carrier acceptance.")

    if "fragile_cargo" in special_cases:
        compliance_flags.append("Fragile cargo requires packing and handling instructions, but this is not usually a customs restriction by itself.")

    missing_documents = _as_list(document_requirements.get("missing_or_unconfirmed_documents"))
    if missing_documents:
        missing_information.extend(f"document: {doc}" for doc in missing_documents)
        recommendations.append("Prepare the required commercial invoice, packing list, and transport document before final compliance review.")

    conditional_documents = _as_list(document_requirements.get("conditional_documents"))
    if conditional_documents:
        recommendations.append("Review conditional documents before booking, especially battery, origin, insurance, and handling documents.")

    if partner_review_status in {
        "partner_review_not_configured",
        "not_configured",
        "not_implemented",
    }:
        warnings.append("Partner Risk, Compliance, Trader, and Finance checks are not connected yet.")
        recommendations.append("Run live partner Compliance, Risk, Trader, and Finance checks before treating this shipment as compliant.")

    elif partner_review_status == "needs_more_information":
        missing_information.append("partner_review_inputs")
        recommendations.append("Provide missing partner-review inputs and rerun compliance review.")

    elif partner_review_status in {"clear", "ready_for_review"}:
        ready_items.append("Partner review is available.")

    if blockers:
        status = "blocked"
        ready_for_partner_review = False
        summary = "Trade compliance readiness is blocked because essential compliance inputs are missing."
    elif missing_information:
        status = "needs_more_information"
        ready_for_partner_review = False
        summary = "Trade compliance readiness needs more information before partner review can be final."
    elif warnings or compliance_flags:
        status = "review_required"
        ready_for_partner_review = True
        summary = "Trade compliance readiness is usable for first-pass review but needs human or partner review."
    else:
        status = "clear"
        ready_for_partner_review = True
        summary = "Trade compliance readiness is clear for first-pass planning."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "ready_for_partner_review": ready_for_partner_review,
        "origin_country": origin_country,
        "destination_country": destination_country,
        "incoterm": incoterm,
        "item_count": len(items),
        "blockers": list(dict.fromkeys(_clean_text(item) for item in blockers)),
        "missing_information": list(dict.fromkeys(_clean_text(item) for item in missing_information))[:12],
        "warnings": list(dict.fromkeys(_clean_text(item) for item in warnings)),
        "compliance_flags": list(dict.fromkeys(_clean_text(item) for item in compliance_flags)),
        "recommendations": list(dict.fromkeys(_clean_text(item) for item in recommendations)),
        "ready_items": list(dict.fromkeys(_clean_text(item) for item in ready_items)),
    }
