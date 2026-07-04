from __future__ import annotations

from typing import Any


REQUIRED_BY_DOCUMENT_TYPE = {
    "invoice": [
        "invoice_number",
        "supplier",
        "origin_country",
        "destination_country",
    ],
    "packing_list": [
        "packing_list_number",
        "supplier",
        "origin_country",
        "destination_country",
    ],
}


def validate_document(parsed_document: dict[str, Any]) -> dict[str, Any]:
    document_type = parsed_document["document_type"]
    fields = parsed_document["fields"]
    items = parsed_document["items"]

    warnings: list[str] = []
    missing_fields: list[str] = []
    recommendations: list[str] = []

    for field in REQUIRED_BY_DOCUMENT_TYPE.get(document_type, []):
        if field not in fields:
            missing_fields.append(field)
            warnings.append(f"Missing required field: {field}")

    if not items:
        warnings.append("No line items were extracted from the document.")
        recommendations.append(
            "Check document formatting or provide a clearer invoice/packing list."
        )

    for item in items:
        if "quantity" not in item:
            warnings.append(f"{item.get('name', 'Unknown item')}: missing quantity.")

        has_dimensions = all(key in item for key in ["length", "width", "height"])
        if document_type == "packing_list" and not has_dimensions:
            warnings.append(
                f"{item.get('name', 'Unknown item')}: packing list item is missing dimensions."
            )

        if "weight" not in item and "total_weight" not in item:
            warnings.append(
                f"{item.get('name', 'Unknown item')}: missing item weight."
            )

    if not warnings:
        warnings.append("No major document validation issues detected.")

    if not recommendations:
        recommendations.append("Document is suitable for first-pass extraction.")

    status = "ready_for_review"

    if missing_fields or not items:
        status = "needs_more_information"
    elif len(warnings) > 1:
        status = "review_required"

    return {
        "status": status,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "recommendations": recommendations,
    }
