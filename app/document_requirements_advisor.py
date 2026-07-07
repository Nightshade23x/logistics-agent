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
        agent_response = _get_specialist_response(user_agent_response, agent_name)
        handoff_payload = _get_handoff_payload(agent_response)

        for container in [agent_response, handoff_payload]:
            for key in ["items", "selected_items", "shipment_items", "cargo_items", "products"]:
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


def _extract_logistics_categories(user_agent_response: dict[str, Any]) -> set[str]:
    logistics_response = _get_specialist_response(user_agent_response, "logistics_agent")
    logistics_handoff = _get_handoff_payload(logistics_response)

    categories = {
        str(category).lower()
        for category in _as_list(logistics_handoff.get("cargo_categories"))
    }

    return categories


def _extract_special_cases(user_agent_response: dict[str, Any]) -> set[str]:
    cases: set[str] = set()

    logistics_quality_review = _get_dict(user_agent_response.get("logistics_quality_review"))
    special_handling = _get_dict(logistics_quality_review.get("special_handling"))
    freight_mode_advice = _get_dict(logistics_quality_review.get("freight_mode_advice"))

    cases.update(
        str(case).lower()
        for case in _as_list(special_handling.get("detected_special_cases"))
    )

    for warning in _as_list(freight_mode_advice.get("warnings")):
        warning_text = str(warning).lower()

        if "fragile" in warning_text:
            cases.add("fragile_cargo")

        if "battery" in warning_text:
            cases.add("battery_possible")

    return cases


def _extract_trade_context(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    trade_terms_advice = _get_dict(user_agent_response.get("trade_terms_advice"))

    origin = (
        trade_terms_advice.get("origin_country")
        or user_agent_response.get("origin_country")
    )

    destination = (
        trade_terms_advice.get("destination_country")
        or user_agent_response.get("destination_country")
    )

    incoterm = trade_terms_advice.get("incoterm")

    return {
        "origin_country": _clean_text(origin) if origin else None,
        "destination_country": _clean_text(destination) if destination else None,
        "incoterm": _clean_text(incoterm).upper() if incoterm else None,
    }


def _extract_document_context(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    document_response = _get_specialist_response(user_agent_response, "document_ai_agent")
    document_quality_review = _get_dict(user_agent_response.get("document_quality_review"))

    detected_document_types = {
        str(doc_type).lower()
        for doc_type in _as_list(document_quality_review.get("detected_document_types"))
    }

    for key in ["document_types", "detected_document_types", "available_documents"]:
        for value in _as_list(document_response.get(key)):
            detected_document_types.add(str(value).lower())

    return {
        "has_document_agent": bool(document_response),
        "detected_document_types": detected_document_types,
        "document_review_status": document_quality_review.get("status"),
    }


def build_document_requirements_advice(
    user_agent_response: dict[str, Any],
) -> dict[str, Any]:
    items = _extract_items(user_agent_response)
    cargo_categories = _extract_logistics_categories(user_agent_response)
    special_cases = _extract_special_cases(user_agent_response)
    trade_context = _extract_trade_context(user_agent_response)
    document_context = _extract_document_context(user_agent_response)

    origin_country = trade_context["origin_country"]
    destination_country = trade_context["destination_country"]
    incoterm = trade_context["incoterm"]

    required_documents = [
        "Commercial invoice",
        "Packing list",
        "Bill of lading or airway bill",
    ]

    conditional_documents: list[str] = []
    missing_or_unconfirmed_documents: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    user_questions: list[str] = []

    if origin_country and destination_country:
        conditional_documents.append("Certificate of origin")
        recommendations.append(
            f"Confirm whether a certificate of origin is needed for {origin_country} to {destination_country}."
        )
    else:
        warnings.append("Origin or destination is missing, so country-specific document checks are incomplete.")
        user_questions.append("What are the confirmed origin and destination countries?")

    if incoterm:
        recommendations.append(f"Make sure all documents use the agreed Incoterm: {incoterm}.")
    else:
        conditional_documents.append("Confirmed Incoterm / shipping terms")
        user_questions.append("Which Incoterm or shipping term should be shown on the invoice and booking documents?")

    if "battery_possible" in special_cases:
        conditional_documents.append("Battery declaration")
        conditional_documents.append("UN38.3 test summary")
        conditional_documents.append("MSDS or battery safety data sheet")
        warnings.append("Possible battery cargo needs battery transport documents before booking.")

    if "hazardous_cargo" in special_cases or "hazardous" in cargo_categories:
        conditional_documents.append("Dangerous goods declaration")
        conditional_documents.append("MSDS")
        warnings.append("Hazardous cargo requires specialist compliance documents and carrier acceptance.")

    if "fragile_cargo" in special_cases or "fragile" in cargo_categories:
        conditional_documents.append("Fragile handling / packing declaration")
        recommendations.append("Add fragile handling notes to packing list and booking instructions.")

    if "temperature_control" in special_cases or "refrigerated" in cargo_categories:
        conditional_documents.append("Temperature-control instructions")
        conditional_documents.append("Temperature range declaration")
        warnings.append("Temperature-sensitive cargo needs documented temperature handling requirements.")

    if "non_stackable" in cargo_categories:
        conditional_documents.append("Non-stackable cargo declaration")
        recommendations.append("Mark non-stackable cargo clearly on packing list and handling instructions.")

    insurance_advice = _get_dict(user_agent_response.get("insurance_advice"))
    insurance_recommendation = insurance_advice.get("insurance_recommendation")

    if insurance_recommendation in {"recommended", "strongly_recommended", "specialist_review_required"}:
        conditional_documents.append("Cargo insurance certificate or insurance confirmation")
        recommendations.append("Keep insurance confirmation with the shipment document pack.")

    detected_types = document_context["detected_document_types"]

    required_checks = {
        "Commercial invoice": ["invoice", "commercial invoice"],
        "Packing list": ["packing", "packing list"],
        "Bill of lading or airway bill": ["bill of lading", "airway bill", "awb", "bl"],
    }

    if document_context["has_document_agent"]:
        for required_doc, markers in required_checks.items():
            if not any(
                any(marker in detected_type for marker in markers)
                for detected_type in detected_types
            ):
                missing_or_unconfirmed_documents.append(required_doc)
    else:
        missing_or_unconfirmed_documents.extend(required_documents)

    if not items:
        warnings.append("No shipment items were available, so document requirements may be incomplete.")
        user_questions.append("Which products and quantities are included in this shipment?")

    if missing_or_unconfirmed_documents:
        status = "review_required"
        summary = "Document requirements advice found documents that are missing or unconfirmed."
    elif warnings:
        status = "review_required"
        summary = "Document requirements advice is usable but needs review."
    else:
        status = "clear"
        summary = "Document requirements advice is clear for first-pass planning."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "origin_country": origin_country,
        "destination_country": destination_country,
        "incoterm": incoterm,
        "item_count": len(items),
        "required_documents": list(dict.fromkeys(required_documents)),
        "conditional_documents": list(dict.fromkeys(_clean_text(item) for item in conditional_documents)),
        "missing_or_unconfirmed_documents": list(dict.fromkeys(_clean_text(item) for item in missing_or_unconfirmed_documents)),
        "warnings": list(dict.fromkeys(_clean_text(item) for item in warnings)),
        "recommendations": list(dict.fromkeys(_clean_text(item) for item in recommendations)),
        "user_questions": list(dict.fromkeys(_clean_text(item) for item in user_questions)),
    }
