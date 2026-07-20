from __future__ import annotations

from pathlib import Path
from typing import Any

from app.document_parser import parse_trade_document, read_document_text


REQUIRED_DOCUMENT_TYPES = [
    "invoice",
    "packing_list",
    "bill_of_lading",
    "certificate_of_origin",
]


def _index_documents(parsed_documents: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}

    for document in parsed_documents:
        document_type = document["document_type"]
        index.setdefault(document_type, []).append(document)

    return index


def _first_document(
    document_index: dict[str, list[dict[str, Any]]],
    document_type: str,
) -> dict[str, Any] | None:
    documents = document_index.get(document_type, [])
    return documents[0] if documents else None


def _field_from_any_document(
    documents: list[dict[str, Any]],
    field_names: list[str],
) -> Any:
    for document in documents:
        fields = document.get("fields", {})
        for field_name in field_names:
            if fields.get(field_name) not in {None, ""}:
                return fields[field_name]

    return None


def _extract_best_items(document_index: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    packing_list = _first_document(document_index, "packing_list")
    invoice = _first_document(document_index, "invoice")

    if packing_list and packing_list.get("items"):
        return packing_list["items"]

    if invoice and invoice.get("items"):
        return invoice["items"]

    return []


def _validate_document_set(parsed_documents: list[dict[str, Any]]) -> dict[str, Any]:
    document_index = _index_documents(parsed_documents)

    present_types = sorted(document_index.keys())
    missing_types = [
        document_type
        for document_type in REQUIRED_DOCUMENT_TYPES
        if document_type not in document_index
    ]

    warnings: list[str] = []
    recommendations: list[str] = []

    for missing_type in missing_types:
        warnings.append(f"Missing required document: {missing_type}")

    for document_type, documents in document_index.items():
        if len(documents) > 1:
            warnings.append(f"Duplicate document type detected: {document_type}")

    origin_values = set()
    destination_values = set()

    for document in parsed_documents:
        fields = document.get("fields", {})
        origin = fields.get("origin_country")
        destination = fields.get("destination_country")

        if origin:
            origin_values.add(str(origin).strip().lower())

        if destination:
            destination_values.add(str(destination).strip().lower())

    if len(origin_values) > 1:
        warnings.append("Origin country is inconsistent across documents.")

    if len(destination_values) > 1:
        warnings.append("Destination country is inconsistent across documents.")

    if missing_types:
        recommendations.append(
            "Request the missing documents before final customs, logistics, or finance processing."
        )

    if len(origin_values) > 1 or len(destination_values) > 1:
        recommendations.append(
            "Correct country inconsistencies before sending data to other agents."
        )

    if not warnings:
        warnings.append("All required core documents are present and no major document-set issues were detected.")

    if not recommendations:
        recommendations.append("Document set is suitable for first-pass multi-agent processing.")

    if missing_types:
        status = "needs_more_information"
    elif len(warnings) > 1 or "inconsistent" in " ".join(warnings).lower():
        status = "review_required"
    else:
        status = "ready_for_review"

    return {
        "status": status,
        "present_document_types": present_types,
        "missing_document_types": missing_types,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def _build_handoff_payload(
    parsed_documents: list[dict[str, Any]],
    validation: dict[str, Any],
) -> dict[str, Any]:
    document_index = _index_documents(parsed_documents)
    all_documents = parsed_documents

    return {
        "documents_present": validation["present_document_types"],
        "documents_missing": validation["missing_document_types"],
        "origin_country": _field_from_any_document(all_documents, ["origin_country"]),
        "destination_country": _field_from_any_document(all_documents, ["destination_country"]),
        "supplier": _field_from_any_document(all_documents, ["supplier", "shipper", "exporter"]),
        "buyer": _field_from_any_document(all_documents, ["buyer", "consignee", "importer"]),
        "currency": _field_from_any_document(all_documents, ["currency"]),
        "total_value": _field_from_any_document(all_documents, ["total_value"]),
        "total_weight_kg": _field_from_any_document(all_documents, ["total_weight_kg"]),
        "items": _extract_best_items(document_index),
        "bill_of_lading_number": _field_from_any_document(all_documents, ["bill_of_lading_number"]),
        "certificate_number": _field_from_any_document(all_documents, ["certificate_number"]),
        "container_number": _field_from_any_document(all_documents, ["container_number"]),
        "seal_number": _field_from_any_document(all_documents, ["seal_number"]),
    }


def _build_handoff_requests(validation: dict[str, Any]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []

    if validation["missing_document_types"]:
        requests.append(
            {
                "target_agent": "user_agent",
                "reason": "Ask the user to provide missing shipment documents.",
                "inputs_needed": [
                    "missing_document_types",
                    "uploaded_documents",
                ],
            }
        )

    requests.extend(
        [
            {
                "target_agent": "logistics_agent",
                "reason": "Use extracted packing and shipment data for CBM, container, and loading planning.",
                "inputs_needed": [
                    "items",
                    "origin_country",
                    "destination_country",
                    "total_weight_kg",
                ],
            },
            {
                "target_agent": "finance_agent",
                "reason": "Use invoice value and shipment data for cost, duty, tax, and insurance estimation.",
                "inputs_needed": [
                    "currency",
                    "total_value",
                    "total_weight_kg",
                    "items",
                ],
            },
            {
                "target_agent": "compliance_agent",
                "reason": "Check documents and extracted products against import/export requirements.",
                "inputs_needed": [
                    "documents_present",
                    "documents_missing",
                    "items",
                    "origin_country",
                    "destination_country",
                ],
            },
        ]
    )

    return requests


def format_document_set_report(
    parsed_documents: list[dict[str, Any]],
    validation: dict[str, Any],
) -> str:
    lines: list[str] = []

    lines.append("DOCUMENT SET COMPLETENESS REPORT")
    lines.append("=" * 40)
    lines.append(f"Validation status: {validation['status']}")
    lines.append("")

    lines.append("DOCUMENTS FOUND")
    lines.append("-" * 40)
    for document in parsed_documents:
        lines.append(f"- {document['document_type']}")
    lines.append("")

    lines.append("REQUIRED DOCUMENT CHECK")
    lines.append("-" * 40)
    lines.append(f"Present: {', '.join(validation['present_document_types'])}")
    if validation["missing_document_types"]:
        lines.append(f"Missing: {', '.join(validation['missing_document_types'])}")
    else:
        lines.append("Missing: none")
    lines.append("")

    lines.append("WARNINGS")
    lines.append("-" * 40)
    for warning in validation["warnings"]:
        lines.append(f"- {warning}")
    lines.append("")

    lines.append("RECOMMENDATIONS")
    lines.append("-" * 40)
    for recommendation in validation["recommendations"]:
        lines.append(f"- {recommendation}")

    return "\n".join(lines)


def run_document_set_agent_from_texts(texts: list[str]) -> dict[str, Any]:
    parsed_documents = [parse_trade_document(text) for text in texts]
    validation = _validate_document_set(parsed_documents)
    report = format_document_set_report(parsed_documents, validation)
    handoff_payload = _build_handoff_payload(parsed_documents, validation)
    handoff_requests = _build_handoff_requests(validation)

    return {
        "agent_name": "document_ai_agent",
        "status": validation["status"],
        "summary": (
            f"Document set status: {validation['status']}. "
            f"Found {len(validation['present_document_types'])} document type(s), "
            f"missing {len(validation['missing_document_types'])} required document type(s)."
        ),
        "plan": {
            "documents": parsed_documents,
            "validation": validation,
        },
        "report": report,
        "input_resolution": {
            "source": "text_set",
            "document_count": len(texts),
        },
        "missing_information": validation["missing_document_types"],
        "handoff_payload": handoff_payload,
        "handoff_requests": handoff_requests,
    }


def run_document_set_agent_from_files(paths: list[str | Path]) -> dict[str, Any]:
    texts = [read_document_text(path) for path in paths]
    response = run_document_set_agent_from_texts(texts)
    response["input_resolution"]["source"] = [str(path) for path in paths]
    return response
