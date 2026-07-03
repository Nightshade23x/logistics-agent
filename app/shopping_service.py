from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.shopping_agent import build_shopping_plan


def read_shopping_request(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _build_handoff_payload(plan: dict[str, Any]) -> dict[str, Any]:
    context = plan["request_context"]
    summary = plan["procurement_summary"]

    return {
        "request_id": context.get("request_id"),
        "customer": context.get("customer"),
        "destination_country": context.get("destination_country"),
        "preferred_currency": context.get("preferred_currency"),
        "selected_items": plan["selected_items"],
        "estimated_total_procurement_cost_usd": summary["estimated_total_procurement_cost_usd"],
        "currency": summary["currency"],
        "supplier_countries": sorted(
            {item["country"] for item in plan["selected_items"] if item.get("country")}
        ),
        "product_categories": sorted(
            {item["category"] for item in plan["selected_items"] if item.get("category")}
        ),
    }


def _build_handoff_requests(plan: dict[str, Any]) -> list[dict[str, Any]]:
    requests = [
        {
            "target_agent": "finance_agent",
            "reason": "Use selected supplier options and procurement costs for total landed cost, ROI, and budget planning.",
            "inputs_needed": [
                "selected_items",
                "estimated_total_procurement_cost_usd",
                "currency",
            ],
        },
        {
            "target_agent": "trader_agent",
            "reason": "Use selected products and supplier countries for HS codes, Incoterms, duties, and trade strategy.",
            "inputs_needed": [
                "selected_items",
                "supplier_countries",
                "destination_country",
            ],
        },
        {
            "target_agent": "compliance_agent",
            "reason": "Check whether selected products or supplier countries have restrictions, permits, or certificates.",
            "inputs_needed": [
                "selected_items",
                "supplier_countries",
                "destination_country",
            ],
        },
    ]

    if plan["issues"]:
        requests.insert(
            0,
            {
                "target_agent": "user_agent",
                "reason": "Ask the user to clarify products or quantities that could not be matched to available suppliers.",
                "inputs_needed": [
                    "issues",
                    "corrected_product_names",
                    "corrected_quantities",
                ],
            },
        )

    return requests


def format_shopping_report(plan: dict[str, Any]) -> str:
    lines = []
    context = plan["request_context"]
    summary = plan["procurement_summary"]

    lines.append("SHOPPING AGENT REPORT")
    lines.append("=" * 30)
    lines.append(f"Request ID: {context.get('request_id')}")
    lines.append(f"Customer: {context.get('customer')}")
    lines.append(f"Destination country: {context.get('destination_country')}")
    lines.append(f"Status: {plan['status']}")
    lines.append("")

    lines.append("PROCUREMENT SUMMARY")
    lines.append("-" * 30)
    lines.append(f"Selected suppliers: {summary['selected_supplier_count']}")
    lines.append(
        f"Estimated total procurement cost: {summary['estimated_total_procurement_cost_usd']} {summary['currency']}"
    )
    lines.append("")

    lines.append("ITEM RESULTS")
    lines.append("-" * 30)

    for result in plan["item_results"]:
        lines.append(f"- {result['requested_item']} x {result['requested_quantity']}")

        if result["issues"]:
            lines.append("  Issues:")
            for issue in result["issues"]:
                lines.append(f"  - {issue}")

        recommendations = result["recommendations"]
        balanced = recommendations.get("balanced")
        cheapest = recommendations.get("cheapest")
        best_quality = recommendations.get("best_quality")

        if balanced:
            lines.append("  Recommended balanced supplier:")
            lines.append(f"  - {balanced['supplier_name']} ({balanced['country']})")
            lines.append(f"    Unit price: {balanced['unit_price_usd']} USD")
            lines.append(f"    Total cost: {balanced['estimated_total_cost_usd']} USD")
            lines.append(f"    Quality score: {balanced['quality_score']}")
            lines.append(f"    Supplier rating: {balanced['supplier_rating']}")
            lines.append(f"    Lead time: {balanced['lead_time_days']} days")
            lines.append(f"    Overall score: {balanced['overall_score']}")

        if cheapest:
            lines.append(
                f"  Cheapest option: {cheapest['supplier_name']} at {cheapest['unit_price_usd']} USD/unit"
            )

        if best_quality:
            lines.append(
                f"  Best quality option: {best_quality['supplier_name']} with quality score {best_quality['quality_score']}"
            )

        if result["alternatives"]:
            lines.append("  Possible alternatives:")
            for alternative in result["alternatives"]:
                lines.append(
                    f"  - {alternative['product_name']} from {alternative['supplier_name']} "
                    f"(similarity {alternative['similarity_score']})"
                )

        lines.append("")

    if plan["issues"]:
        lines.append("ISSUES")
        lines.append("-" * 30)
        for issue in plan["issues"]:
            lines.append(f"- {issue}")

    return "\n".join(lines)


def run_shopping_agent(request_data: dict[str, Any]) -> dict[str, Any]:
    plan = build_shopping_plan(request_data)
    report = format_shopping_report(plan)
    handoff_payload = _build_handoff_payload(plan)
    handoff_requests = _build_handoff_requests(plan)

    return {
        "agent_name": "shopping_agent",
        "status": plan["status"],
        "summary": (
            f"Shopping Agent status: {plan['status']}. "
            f"Selected {plan['procurement_summary']['selected_supplier_count']} supplier option(s). "
            f"Estimated procurement cost: {plan['procurement_summary']['estimated_total_procurement_cost_usd']} USD."
        ),
        "plan": plan,
        "report": report,
        "input_resolution": {
            "source": "shopping_request",
            "catalog_size": plan["catalog_size"],
        },
        "missing_information": plan["issues"],
        "handoff_payload": handoff_payload,
        "handoff_requests": handoff_requests,
    }


def run_shopping_agent_from_file(path: str | Path) -> dict[str, Any]:
    request_data = read_shopping_request(path)
    response = run_shopping_agent(request_data)
    response["input_resolution"]["source"] = str(path)
    return response
