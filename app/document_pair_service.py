from __future__ import annotations

from pathlib import Path
from typing import Any

from app.document_consistency import compare_invoice_and_packing_list
from app.document_parser import parse_trade_document, read_document_text


def _build_handoff_payload(
    invoice_document: dict[str, Any],
    packing_list_document: dict[str, Any],
    consistency: dict[str, Any],
) -> dict[str, Any]:
    invoice_fields = invoice_document.get("fields", {})
    packing_fields = packing_list_document.get("fields", {})

    return {
        "document_pair": ["invoice", "packing_list"],
        "invoice_fields": invoice_fields,
        "packing_list_fields": packing_fields,
        "origin_country": packing_fields.get("origin_country") or invoice_fields.get("origin_country"),
        "destination_country": packing_fields.get("destination_country") or invoice_fields.get("destination_country"),
        "supplier": packing_fields.get("supplier") or invoice_fields.get("supplier"),
        "currency": invoice_fields.get("currency"),
        "total_value": invoice_fields.get("total_value"),
        "total_weight_kg": packing_fields.get("total_weight_kg") or invoice_fields.get("total_weight_kg"),
        "items": consistency["matched_items"],
        "mismatch_count": consistency["comparison_summary"]["mismatch_count"],
    }


def _build_handoff_requests(consistency: dict[str, Any]) -> list[dict[str, Any]]:
    requests = [
        {
            "target_agent": "logistics_agent",
            "reason": "Use validated packing list items for CBM, container, loading, and shipping planning.",
            "inputs_needed": [
                "items",
                "origin_country",
                "destination_country",
                "total_weight_kg",
            ],
        },
        {
            "target_agent": "finance_agent",
            "reason": "Use invoice value and validated shipment data for tax, duty, insurance, and cost estimation.",
            "inputs_needed": [
                "currency",
                "total_value",
                "items",
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
    ]

    if consistency["mismatches"]:
        requests.insert(
            0,
            {
                "target_agent": "user_agent",
                "reason": "Ask the user to correct invoice and packing list mismatches before final shipment planning.",
                "inputs_needed": [
                    "mismatches",
                    "corrected_invoice_or_packing_list",
                ],
            },
        )

    return requests


def format_document_pair_report(
    invoice_document: dict[str, Any],
    packing_list_document: dict[str, Any],
    consistency: dict[str, Any],
) -> str:
    lines: list[str] = []

    lines.append("DOCUMENT PAIR VALIDATION REPORT")
    lines.append("=" * 40)
    lines.append(f"Invoice document type: {invoice_document['document_type']}")
    lines.append(f"Packing list document type: {packing_list_document['document_type']}")
    lines.append(f"Validation status: {consistency['status']}")
    lines.append("")

    lines.append("COMPARISON SUMMARY")
    lines.append("-" * 40)
    summary = consistency["comparison_summary"]
    lines.append(f"Invoice items: {summary['invoice_items']}")
    lines.append(f"Packing list items: {summary['packing_list_items']}")
    lines.append(f"Matched or checked items: {summary['matched_or_checked_items']}")
    lines.append(f"Mismatch count: {summary['mismatch_count']}")
    lines.append("")

    lines.append("WARNINGS")
    lines.append("-" * 40)
    for warning in consistency["warnings"]:
        lines.append(f"- {warning}")
    lines.append("")

    lines.append("MISMATCHES")
    lines.append("-" * 40)
    if consistency["mismatches"]:
        for mismatch in consistency["mismatches"]:
            lines.append(f"- {mismatch}")
    else:
        lines.append("- No invoice vs packing list mismatches detected.")
    lines.append("")

    lines.append("MATCHED ITEMS FOR HANDOFF")
    lines.append("-" * 40)
    for item in consistency["matched_items"]:
        lines.append(f"- {item.get('name')} x {item.get('quantity')}")
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
    lines.append("")

    lines.append("RECOMMENDATIONS")
    lines.append("-" * 40)
    for recommendation in consistency["recommendations"]:
        lines.append(f"- {recommendation}")

    return "\n".join(lines)


def run_document_pair_agent_from_texts(
    invoice_text: str,
    packing_list_text: str,
) -> dict[str, Any]:
    invoice_document = parse_trade_document(invoice_text)
    packing_list_document = parse_trade_document(packing_list_text)

    consistency = compare_invoice_and_packing_list(
        invoice_document,
        packing_list_document,
    )

    report = format_document_pair_report(
        invoice_document,
        packing_list_document,
        consistency,
    )

    handoff_payload = _build_handoff_payload(
        invoice_document,
        packing_list_document,
        consistency,
    )

    handoff_requests = _build_handoff_requests(consistency)

    return {
        "agent_name": "document_ai_agent",
        "status": consistency["status"],
        "summary": (
            f"Document pair validation status: {consistency['status']}. "
            f"Found {consistency['comparison_summary']['mismatch_count']} mismatch(es)."
        ),
        "plan": {
            "invoice": invoice_document,
            "packing_list": packing_list_document,
            "consistency": consistency,
        },
        "report": report,
        "input_resolution": {
            "source": "text_pair",
            "documents": ["invoice", "packing_list"],
        },
        "missing_information": consistency["mismatches"],
        "handoff_payload": handoff_payload,
        "handoff_requests": handoff_requests,
    }


def run_document_pair_agent_from_files(
    invoice_path: str | Path,
    packing_list_path: str | Path,
) -> dict[str, Any]:
    invoice_text = read_document_text(invoice_path)
    packing_list_text = read_document_text(packing_list_path)

    response = run_document_pair_agent_from_texts(invoice_text, packing_list_text)
    response["input_resolution"]["source"] = {
        "invoice_path": str(invoice_path),
        "packing_list_path": str(packing_list_path),
    }

    return response
