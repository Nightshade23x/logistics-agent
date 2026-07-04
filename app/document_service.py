from __future__ import annotations

from pathlib import Path
from typing import Any

from app.document_parser import parse_trade_document, read_document_text
from app.document_validator import validate_document


def _build_handoff_payload(parsed_document: dict[str, Any]) -> dict[str, Any]:
    fields = parsed_document["fields"]

    return {
        "document_type": parsed_document["document_type"],
        "supplier": fields.get("supplier"),
        "buyer": fields.get("buyer"),
        "origin_country": fields.get("origin_country"),
        "destination_country": fields.get("destination_country"),
        "currency": fields.get("currency"),
        "total_value": fields.get("total_value"),
        "total_weight_kg": fields.get("total_weight_kg"),
        "items": parsed_document["items"],
    }


def _build_handoff_requests(parsed_document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "target_agent": "logistics_agent",
            "reason": "Use extracted products, quantities, dimensions, and weights for CBM, container, and loading planning.",
            "inputs_needed": [
                "items",
                "origin_country",
                "destination_country",
                "total_weight_kg",
            ],
        },
        {
            "target_agent": "compliance_agent",
            "reason": "Check whether extracted products are allowed, restricted, or prohibited.",
            "inputs_needed": [
                "items",
                "origin_country",
                "destination_country",
            ],
        },
        {
            "target_agent": "finance_agent",
            "reason": "Use extracted invoice values and weights for cost, tax, duty, and insurance estimation.",
            "inputs_needed": [
                "items",
                "currency",
                "total_value",
                "total_weight_kg",
            ],
        },
    ]


def format_document_report(parsed_document: dict[str, Any], validation: dict[str, Any]) -> str:
    fields = parsed_document["fields"]
    items = parsed_document["items"]

    lines: list[str] = []

    lines.append("DOCUMENT AI REPORT")
    lines.append("=" * 30)
    lines.append(f"Document type: {parsed_document['document_type']}")
    lines.append(f"Validation status: {validation['status']}")
    lines.append("")

    lines.append("EXTRACTED FIELDS")
    lines.append("-" * 30)
    if fields:
        for key, value in fields.items():
            lines.append(f"{key}: {value}")
    else:
        lines.append("No header fields extracted.")
    lines.append("")

    lines.append("EXTRACTED ITEMS")
    lines.append("-" * 30)
    if items:
        for item in items:
            lines.append(f"- {item['name']} x {item['quantity']}")
            if all(key in item for key in ["length", "width", "height"]):
                lines.append(
                    f"  Dimensions: {item['length']} x {item['width']} x {item['height']} {item.get('dimension_unit', '')}"
                )
            if "weight" in item:
                lines.append(f"  Unit weight: {item['weight']} {item.get('weight_unit', '')}")
            if "total_weight" in item:
                lines.append(
                    f"  Total weight: {item['total_weight']} {item.get('total_weight_unit', '')}"
                )
    else:
        lines.append("No items extracted.")
    lines.append("")

    lines.append("VALIDATION WARNINGS")
    lines.append("-" * 30)
    for warning in validation["warnings"]:
        lines.append(f"- {warning}")
    lines.append("")

    lines.append("RECOMMENDATIONS")
    lines.append("-" * 30)
    for recommendation in validation["recommendations"]:
        lines.append(f"- {recommendation}")

    return "\n".join(lines)


def run_document_agent_from_text(text: str) -> dict[str, Any]:
    parsed_document = parse_trade_document(text)
    validation = validate_document(parsed_document)
    report = format_document_report(parsed_document, validation)
    handoff_payload = _build_handoff_payload(parsed_document)
    handoff_requests = _build_handoff_requests(parsed_document)

    return {
        "agent_name": "document_ai_agent",
        "status": validation["status"],
        "summary": (
            f"Document AI status: {validation['status']}. "
            f"Detected document type: {parsed_document['document_type']}. "
            f"Extracted {len(parsed_document['items'])} item(s)."
        ),
        "plan": parsed_document,
        "report": report,
        "input_resolution": {
            "source": "text",
            "document_type": parsed_document["document_type"],
        },
        "missing_information": validation["missing_fields"],
        "handoff_payload": handoff_payload,
        "handoff_requests": handoff_requests,
    }


def run_document_agent_from_file(path: str | Path) -> dict[str, Any]:
    text = read_document_text(path)
    response = run_document_agent_from_text(text)
    response["input_resolution"]["source"] = str(path)
    return response
