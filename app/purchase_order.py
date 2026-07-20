from __future__ import annotations

from typing import Any


def _safe_id_part(value: str | None) -> str:
    if not value:
        return "UNKNOWN"

    cleaned = "".join(
        character.upper()
        for character in str(value)
        if character.isalnum()
    )

    return cleaned[:12] or "UNKNOWN"


def generate_purchase_order_drafts(plan: dict[str, Any]) -> list[dict[str, Any]]:
    context = plan["request_context"]
    selected_items = plan["selected_items"]

    grouped: dict[str, dict[str, Any]] = {}

    for item in selected_items:
        supplier_id = item["supplier_id"]

        if supplier_id not in grouped:
            grouped[supplier_id] = {
                "purchase_order_id": (
                    f"PO-{_safe_id_part(context.get('request_id'))}-{_safe_id_part(supplier_id)}"
                ),
                "status": "draft",
                "buyer": context.get("customer"),
                "destination_country": context.get("destination_country"),
                "supplier_id": item["supplier_id"],
                "supplier_name": item["supplier_name"],
                "supplier_country": item["country"],
                "currency": "USD",
                "line_items": [],
                "total_amount_usd": 0.0,
                "risk_level": item.get("risk_level", "unknown"),
                "risk_score": item.get("risk_score", 0),
                "risk_notes": [],
                "review_notes": [
                    "Draft purchase order only; supplier details must be verified before sending.",
                    "Confirm Incoterms, payment terms, delivery terms, and final availability.",
                    "Finance Agent should confirm total landed cost before approval.",
                    "Compliance Agent should confirm product and country requirements before approval.",
                ],
            }

        purchase_order = grouped[supplier_id]

        purchase_order["line_items"].append(
            {
                "product_name": item["product_name"],
                "category": item["category"],
                "quantity": item["requested_quantity"],
                "unit_price_usd": item["unit_price_usd"],
                "line_total_usd": item["estimated_total_cost_usd"],
                "lead_time_days": item["lead_time_days"],
                "quality_score": item["quality_score"],
                "supplier_rating": item["supplier_rating"],
            }
        )

        purchase_order["total_amount_usd"] += float(item["estimated_total_cost_usd"])

        if int(item.get("risk_score", 0)) > int(purchase_order.get("risk_score", 0)):
            purchase_order["risk_score"] = item.get("risk_score", 0)
            purchase_order["risk_level"] = item.get("risk_level", "unknown")

        for note in item.get("risk_notes", []):
            if note not in purchase_order["risk_notes"]:
                purchase_order["risk_notes"].append(note)

    drafts = list(grouped.values())

    for draft in drafts:
        draft["total_amount_usd"] = round(draft["total_amount_usd"], 2)

    return drafts


def format_purchase_order_drafts(purchase_order_drafts: list[dict[str, Any]]) -> str:
    if not purchase_order_drafts:
        return "No purchase order drafts were created."

    lines: list[str] = []

    for draft in purchase_order_drafts:
        lines.append(f"Purchase Order: {draft['purchase_order_id']}")
        lines.append(f"Status: {draft['status']}")
        lines.append(f"Buyer: {draft['buyer']}")
        lines.append(f"Supplier: {draft['supplier_name']} ({draft['supplier_country']})")
        lines.append(f"Destination country: {draft['destination_country']}")
        lines.append(f"Total amount: {draft['total_amount_usd']} {draft['currency']}")
        lines.append(f"Risk level: {draft['risk_level']} ({draft['risk_score']}/10)")
        lines.append("Line items:")

        for item in draft["line_items"]:
            lines.append(
                f"- {item['product_name']} x {item['quantity']} "
                f"@ {item['unit_price_usd']} USD = {item['line_total_usd']} USD"
            )

        if draft["risk_notes"]:
            lines.append("Risk notes:")
            for note in draft["risk_notes"]:
                lines.append(f"- {note}")

        lines.append("Review notes:")
        for note in draft["review_notes"]:
            lines.append(f"- {note}")

        lines.append("")

    return "\n".join(lines).strip()
