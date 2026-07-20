from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def build_supplier_shortlist(plan: dict[str, Any]) -> list[dict[str, Any]]:
    shortlist: list[dict[str, Any]] = []

    for result in plan["item_results"]:
        requested_item = result["requested_item"]
        requested_quantity = result["requested_quantity"]
        balanced_supplier_id = None

        balanced = result["recommendations"].get("balanced")
        if balanced:
            balanced_supplier_id = balanced["supplier_id"]

        for option in result["supplier_options"]:
            shortlist.append(
                {
                    "requested_item": requested_item,
                    "requested_quantity": requested_quantity,
                    "supplier_id": option["supplier_id"],
                    "supplier_name": option["supplier_name"],
                    "supplier_country": option["country"],
                    "product_name": option["product_name"],
                    "category": option["category"],
                    "unit_price_usd": option["unit_price_usd"],
                    "estimated_total_cost_usd": option["estimated_total_cost_usd"],
                    "quality_score": option["quality_score"],
                    "supplier_rating": option["supplier_rating"],
                    "lead_time_days": option["lead_time_days"],
                    "available_quantity": option["available_quantity"],
                    "minimum_order_quantity": option["minimum_order_quantity"],
                    "selection_status": option["selection_status"],
                    "availability_status": option["availability_status"],
                    "preference_issues": option["preference_issues"],
                    "overall_score": option["overall_score"],
                    "risk_level": option["risk_level"],
                    "risk_score": option["risk_score"],
                    "is_selected": option["supplier_id"] == balanced_supplier_id,
                    "notes": option.get("notes", ""),
                }
            )

    return sorted(
        shortlist,
        key=lambda item: (
            not item["is_selected"],
            item["requested_item"],
            item["selection_status"] != "eligible",
            -float(item["overall_score"]),
            float(item["unit_price_usd"]),
        ),
    )


def format_supplier_shortlist(shortlist: list[dict[str, Any]]) -> str:
    if not shortlist:
        return "No supplier shortlist was created."

    lines: list[str] = []

    current_item = None

    for option in shortlist:
        if option["requested_item"] != current_item:
            current_item = option["requested_item"]
            lines.append(f"{current_item} x {option['requested_quantity']}")

        selected_marker = "selected" if option["is_selected"] else "candidate"
        issues = option["preference_issues"] or []

        lines.append(
            f"- {option['supplier_name']} ({option['supplier_country']}) "
            f"[{selected_marker}, {option['selection_status']}]"
        )
        lines.append(
            f"  Price: {option['unit_price_usd']} USD/unit | "
            f"Total: {option['estimated_total_cost_usd']} USD | "
            f"Lead time: {option['lead_time_days']} days"
        )
        lines.append(
            f"  Quality: {option['quality_score']} | "
            f"Rating: {option['supplier_rating']} | "
            f"Score: {option['overall_score']} | "
            f"Risk: {option['risk_level']} ({option['risk_score']}/10)"
        )

        if issues:
            lines.append(f"  Filter reasons: {', '.join(issues)}")

    return "\n".join(lines)


def export_supplier_shortlist_json(
    shortlist: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(shortlist, indent=2), encoding="utf-8")
    return path


def export_supplier_shortlist_csv(
    shortlist: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "requested_item",
        "requested_quantity",
        "supplier_id",
        "supplier_name",
        "supplier_country",
        "product_name",
        "category",
        "unit_price_usd",
        "estimated_total_cost_usd",
        "quality_score",
        "supplier_rating",
        "lead_time_days",
        "available_quantity",
        "minimum_order_quantity",
        "selection_status",
        "availability_status",
        "preference_issues",
        "overall_score",
        "risk_level",
        "risk_score",
        "is_selected",
        "notes",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for item in shortlist:
            row = dict(item)
            row["preference_issues"] = ", ".join(row.get("preference_issues", []))
            writer.writerow(row)

    return path
