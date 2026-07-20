from __future__ import annotations

from typing import Any


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().strip().replace("-", " ").split())


def _item_key(item: dict[str, Any]) -> str:
    return _normalize_name(str(item.get("name", "")))


def _to_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_item_index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        _item_key(item): item
        for item in items
        if item.get("name")
    }


def _computed_total_weight(item: dict[str, Any]) -> float | None:
    quantity = _to_float(item.get("quantity"))
    unit_weight = _to_float(item.get("weight"))
    total_weight = _to_float(item.get("total_weight"))

    if total_weight is not None:
        return total_weight

    if quantity is not None and unit_weight is not None:
        return quantity * unit_weight

    return None


def _compare_field(
    field_name: str,
    invoice_fields: dict[str, Any],
    packing_fields: dict[str, Any],
    mismatches: list[str],
) -> None:
    invoice_value = invoice_fields.get(field_name)
    packing_value = packing_fields.get(field_name)

    if invoice_value is None or packing_value is None:
        return

    if str(invoice_value).strip().lower() != str(packing_value).strip().lower():
        mismatches.append(
            f"{field_name}: invoice has '{invoice_value}' but packing list has '{packing_value}'."
        )


def _merge_item_for_handoff(
    item_name: str,
    invoice_item: dict[str, Any] | None,
    packing_item: dict[str, Any] | None,
) -> dict[str, Any]:
    source_item = packing_item or invoice_item or {}

    merged: dict[str, Any] = {
        "name": source_item.get("name", item_name),
        "quantity": source_item.get("quantity"),
    }

    if packing_item:
        for key in ["length", "width", "height", "dimension_unit", "weight", "weight_unit"]:
            if key in packing_item:
                merged[key] = packing_item[key]

    if packing_item:
        packing_total_weight = _computed_total_weight(packing_item)
        if packing_total_weight is not None:
            merged["total_weight"] = packing_total_weight
            merged["total_weight_unit"] = packing_item.get("weight_unit", "kg")
    elif invoice_item:
        invoice_total_weight = _computed_total_weight(invoice_item)
        if invoice_total_weight is not None:
            merged["total_weight"] = invoice_total_weight
            merged["total_weight_unit"] = invoice_item.get("total_weight_unit", invoice_item.get("weight_unit", "kg"))

    return merged


def compare_invoice_and_packing_list(
    invoice_document: dict[str, Any],
    packing_list_document: dict[str, Any],
) -> dict[str, Any]:
    invoice_fields = invoice_document.get("fields", {})
    packing_fields = packing_list_document.get("fields", {})

    invoice_items = invoice_document.get("items", [])
    packing_items = packing_list_document.get("items", [])

    invoice_index = _build_item_index(invoice_items)
    packing_index = _build_item_index(packing_items)

    warnings: list[str] = []
    mismatches: list[str] = []
    recommendations: list[str] = []
    matched_items: list[dict[str, Any]] = []

    if invoice_document.get("document_type") != "invoice":
        warnings.append("First document is not detected as an invoice.")

    if packing_list_document.get("document_type") != "packing_list":
        warnings.append("Second document is not detected as a packing list.")

    for field in ["supplier", "origin_country", "destination_country"]:
        _compare_field(field, invoice_fields, packing_fields, mismatches)

    invoice_total_weight = _to_float(invoice_fields.get("total_weight_kg"))
    packing_total_weight = _to_float(packing_fields.get("total_weight_kg"))

    if invoice_total_weight is not None and packing_total_weight is not None:
        if round(invoice_total_weight, 2) != round(packing_total_weight, 2):
            mismatches.append(
                f"total_weight_kg: invoice has {invoice_total_weight} kg but packing list has {packing_total_weight} kg."
            )

    all_item_keys = sorted(set(invoice_index).union(set(packing_index)))

    for key in all_item_keys:
        invoice_item = invoice_index.get(key)
        packing_item = packing_index.get(key)

        if invoice_item is None:
            mismatches.append(
                f"{packing_item['name']}: appears in packing list but is missing from invoice."
            )
            matched_items.append(_merge_item_for_handoff(key, invoice_item, packing_item))
            continue

        if packing_item is None:
            mismatches.append(
                f"{invoice_item['name']}: appears in invoice but is missing from packing list."
            )
            matched_items.append(_merge_item_for_handoff(key, invoice_item, packing_item))
            continue

        invoice_quantity = invoice_item.get("quantity")
        packing_quantity = packing_item.get("quantity")

        if invoice_quantity != packing_quantity:
            mismatches.append(
                f"{invoice_item['name']}: invoice quantity is {invoice_quantity}, packing list quantity is {packing_quantity}."
            )

        invoice_weight = _computed_total_weight(invoice_item)
        packing_weight = _computed_total_weight(packing_item)

        if invoice_weight is not None and packing_weight is not None:
            if round(invoice_weight, 2) != round(packing_weight, 2):
                mismatches.append(
                    f"{invoice_item['name']}: invoice total weight is {invoice_weight} kg, packing list total weight is {packing_weight} kg."
                )

        matched_items.append(_merge_item_for_handoff(key, invoice_item, packing_item))

    if mismatches:
        recommendations.append(
            "Review and correct the invoice and packing list before using them for customs, logistics, or finance calculations."
        )
    else:
        recommendations.append(
            "Invoice and packing list appear consistent for first-pass document validation."
        )

    if not warnings:
        warnings.append("No major document type warnings detected.")

    if mismatches:
        status = "review_required"
    else:
        status = "ready_for_review"

    return {
        "status": status,
        "warnings": warnings,
        "mismatches": mismatches,
        "recommendations": recommendations,
        "matched_items": matched_items,
        "comparison_summary": {
            "invoice_items": len(invoice_items),
            "packing_list_items": len(packing_items),
            "matched_or_checked_items": len(matched_items),
            "mismatch_count": len(mismatches),
        },
    }
