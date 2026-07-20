from __future__ import annotations

from typing import Any


def _get_document_response(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    specialist_responses = user_agent_response.get("specialist_responses", {})
    document_response = specialist_responses.get("document_ai_agent", {})

    if isinstance(document_response, dict):
        return document_response

    return {}


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _clean_text(value: Any) -> str:
    return " ".join(str(value).split())


def _collect_values_by_key(data: Any, target_keys: set[str]) -> list[Any]:
    values: list[Any] = []

    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in target_keys:
                values.append(value)

            values.extend(_collect_values_by_key(value, target_keys))

    elif isinstance(data, list):
        for item in data:
            values.extend(_collect_values_by_key(item, target_keys))

    return values


def _count_document_types(document_response: dict[str, Any]) -> set[str]:
    found_types: set[str] = set()

    possible_docs = []
    possible_docs.extend(_as_list(document_response.get("documents")))
    possible_docs.extend(_as_list(document_response.get("parsed_documents")))
    possible_docs.extend(_as_list(document_response.get("extracted_documents")))

    handoff_payload = document_response.get("handoff_payload", {})
    if isinstance(handoff_payload, dict):
        possible_docs.extend(_as_list(handoff_payload.get("documents")))
        possible_docs.extend(_as_list(handoff_payload.get("parsed_documents")))

    for doc in possible_docs:
        if not isinstance(doc, dict):
            continue

        doc_type = (
            doc.get("document_type")
            or doc.get("type")
            or doc.get("doc_type")
            or doc.get("classification")
        )

        if doc_type:
            found_types.add(str(doc_type).strip().lower())

    return found_types


def build_document_quality_review(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    document_response = _get_document_response(user_agent_response)

    if not document_response:
        return {
            "applicable": False,
            "status": "not_applicable",
            "summary": "No Document AI Agent response was found for this request.",
            "blockers": [],
            "warnings": [],
            "recommendations": [],
        }

    response_status = str(document_response.get("status", "")).lower()
    handoff_payload = document_response.get("handoff_payload", {})
    if not isinstance(handoff_payload, dict):
        handoff_payload = {}

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    if response_status in {"blocked", "error"}:
        blockers.append(f"Document AI Agent returned status: {response_status}.")

    if response_status in {"needs_more_information", "partial_plan_needs_more_information"}:
        warnings.append(f"Document AI Agent returned status: {response_status}.")

    if response_status in {"review_required", "critical_review_required"}:
        warnings.append(f"Document AI Agent marked the document set as {response_status}.")

    mismatch_values = _collect_values_by_key(
        document_response,
        {"mismatch_count", "mismatches_count", "consistency_mismatch_count"},
    )

    mismatch_count = 0
    for value in mismatch_values:
        number = _as_int(value)
        if number is not None:
            mismatch_count = max(mismatch_count, number)

    if mismatch_count > 0:
        blockers.append(f"Document set has {mismatch_count} invoice/packing-list mismatch(es).")
        recommendations.append("Resolve document mismatches before using the shipment data for booking or partner review.")

    consistency_values = _collect_values_by_key(
        document_response,
        {"consistency_status", "document_consistency_status", "comparison_status"},
    )

    for value in consistency_values:
        value_text = str(value).lower()
        if any(marker in value_text for marker in ["mismatch", "failed", "inconsistent"]):
            blockers.append(f"Document consistency check returned: {_clean_text(value)}.")

    missing_information = _as_list(document_response.get("missing_information"))
    missing_information.extend(_as_list(handoff_payload.get("missing_information")))

    for item in missing_information:
        item_text = _clean_text(item)
        if item_text:
            warnings.append(item_text)

    validation_errors = _collect_values_by_key(
        document_response,
        {"validation_errors", "errors", "blocking_errors"},
    )

    for value in validation_errors:
        for item in _as_list(value):
            item_text = _clean_text(item)
            if item_text:
                blockers.append(item_text)

    validation_warnings = _collect_values_by_key(
        document_response,
        {"validation_warnings", "warnings"},
    )

    for value in validation_warnings:
        for item in _as_list(value):
            item_text = _clean_text(item)
            if item_text:
                warnings.append(item_text)

    confidence_values = _collect_values_by_key(
        document_response,
        {"confidence", "extraction_confidence", "average_confidence"},
    )

    low_confidence_count = 0
    for value in confidence_values:
        confidence = _as_float(value)
        if confidence is not None and confidence < 0.75:
            low_confidence_count += 1

    if low_confidence_count:
        warnings.append(f"{low_confidence_count} document extraction confidence value(s) are below 0.75.")
        recommendations.append("Review low-confidence extracted fields manually.")

    document_types = _count_document_types(document_response)

    if document_types:
        has_invoice = any("invoice" in doc_type for doc_type in document_types)
        has_packing_list = any("packing" in doc_type for doc_type in document_types)

        if not has_invoice:
            warnings.append("No invoice document type was detected.")

        if not has_packing_list:
            warnings.append("No packing list document type was detected.")

    extracted_items = None

    for source in [handoff_payload, document_response]:
        if not isinstance(source, dict):
            continue

        for key in ["items", "selected_items", "shipment_items"]:
            if key in source:
                extracted_items = source.get(key)
                break

        if extracted_items is not None:
            break

    if isinstance(extracted_items, list) and len(extracted_items) == 0:
        blockers.append("No shipment items were extracted from the documents.")

    if blockers:
        status = "blocked"
        summary = "Document review found blockers that must be resolved before shipment planning."
    elif warnings:
        status = "review_required"
        summary = "Document review is usable but should be checked before shipment planning."
    else:
        status = "clear"
        summary = "Document review is usable for first-pass shipment planning."

    unique_blockers = list(dict.fromkeys(blockers))
    unique_warnings = list(dict.fromkeys(warnings))
    unique_recommendations = list(dict.fromkeys(recommendations))

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "document_agent_status": response_status or None,
        "mismatch_count": mismatch_count,
        "detected_document_types": sorted(document_types),
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "recommendations": unique_recommendations,
    }
