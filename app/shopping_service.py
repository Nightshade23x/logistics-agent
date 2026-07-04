from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.shopping_agent import build_shopping_plan
from app.shopping_text_parser import parse_shopping_request_text


def read_shopping_request(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def read_shopping_request_text(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as file:
        return parse_shopping_request_text(file.read())


def _build_handoff_payload(plan: dict[str, Any]) -> dict[str, Any]:
    context = plan["request_context"]
    summary = plan["procurement_summary"]

    return {
        "request_id": context.get("request_id"),
        "customer": context.get("customer"),
        "destination_country": context.get("destination_country"),
        "preferred_currency": context.get("preferred_currency"),
        "preferences": plan["preferences"],
        "selected_items": plan["selected_items"],
        "estimated_total_procurement_cost_usd": summary["estimated_total_procurement_cost_usd"],
        "currency": summary["currency"],
        "budget_check": plan["budget_check"],
        "procurement_risk": plan["procurement_risk"],
        "supplier_countries": sorted(
            {
                item["country"]
                for item in plan["selected_items"]
                if item.get("country")
            }
        ),
        "product_categories": sorted(
            {
                item["category"]
                for item in plan["selected_items"]
                if item.get("category")
            }
        ),
    }


def _build_handoff_requests(plan: dict[str, Any]) -> list[dict[str, Any]]:
    requests = [
        {
            "target_agent": "finance_agent",
            "reason": "Use selected supplier options, budget check, procurement risk, and procurement costs for total landed cost, ROI, and budget planning.",
            "inputs_needed": [
                "selected_items",
                "estimated_total_procurement_cost_usd",
                "currency",
                "budget_check",
                "procurement_risk",
            ],
        },
        {
            "target_agent": "trader_agent",
            "reason": "Use selected products, supplier countries, and procurement risk for HS codes, Incoterms, duties, and trade strategy.",
            "inputs_needed": [
                "selected_items",
                "supplier_countries",
                "destination_country",
                "procurement_risk",
            ],
        },
        {
            "target_agent": "compliance_agent",
            "reason": "Check whether selected products, supplier countries, or procurement risks require restrictions, permits, or certificates.",
            "inputs_needed": [
                "selected_items",
                "supplier_countries",
                "destination_country",
                "procurement_risk",
            ],
        },
    ]

    if plan["issues"]:
        requests.insert(
            0,
            {
                "target_agent": "user_agent",
                "reason": "Ask the user to clarify product requirements, budget, supplier preferences, or risk tolerance.",
                "inputs_needed": [
                    "issues",
                    "corrected_product_names",
                    "corrected_quantities",
                    "revised_budget",
                    "revised_supplier_preferences",
                    "risk_tolerance",
                ],
            },
        )

    return requests


def _preferences_are_present(preferences: dict[str, Any]) -> bool:
    return any(
        value not in (None, [], "")
        for value in preferences.values()
    )


def format_shopping_report(plan: dict[str, Any]) -> str:
    lines = []

    context = plan["request_context"]
    summary = plan["procurement_summary"]
    preferences = plan["preferences"]
    budget_check = plan["budget_check"]
    procurement_risk = plan["procurement_risk"]

    lines.append("SHOPPING AGENT REPORT")
    lines.append("=" * 30)
    lines.append(f"Request ID: {context.get('request_id')}")
    lines.append(f"Customer: {context.get('customer')}")
    lines.append(f"Destination country: {context.get('destination_country')}")
    lines.append(f"Status: {plan['status']}")
    lines.append("")

    if _preferences_are_present(preferences):
        lines.append("PREFERENCES AND CONSTRAINTS")
        lines.append("-" * 30)
        lines.append(f"Preferred supplier countries: {preferences['preferred_supplier_countries'] or 'none'}")
        lines.append(f"Excluded supplier countries: {preferences['excluded_supplier_countries'] or 'none'}")
        lines.append(f"Max lead time days: {preferences['max_lead_time_days'] or 'none'}")
        lines.append(f"Minimum quality score: {preferences['minimum_quality_score'] or 'none'}")
        lines.append(f"Max budget USD: {preferences['max_budget_usd'] or 'none'}")
        lines.append("")

    lines.append("PROCUREMENT SUMMARY")
    lines.append("-" * 30)
    lines.append(f"Selected suppliers: {summary['selected_supplier_count']}")
    lines.append(
        f"Estimated total procurement cost: {summary['estimated_total_procurement_cost_usd']} {summary['currency']}"
    )

    if budget_check["max_budget_usd"] is not None:
        lines.append(f"Budget limit: {budget_check['max_budget_usd']} USD")
        lines.append(f"Within budget: {budget_check['within_budget']}")

    lines.append("")

    lines.append("PROCUREMENT RISK")
    lines.append("-" * 30)
    lines.append(f"Overall risk level: {procurement_risk['overall_risk_level']}")
    lines.append(f"Overall risk score: {procurement_risk['overall_risk_score']}/10")

    if procurement_risk["highest_risk_items"]:
        lines.append("Highest risk items:")
        for item in procurement_risk["highest_risk_items"]:
            lines.append(
                f"- {item['product_name']} from {item['supplier_name']} "
                f"({item['risk_level']}, {item['risk_score']}/10)"
            )

    if procurement_risk["risk_notes"]:
        lines.append("Risk notes:")
        for note in procurement_risk["risk_notes"]:
            lines.append(f"- {note}")

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
            lines.append(f"    Preferred country: {balanced['is_preferred_country']}")
            lines.append(f"    Overall score: {balanced['overall_score']}")
            lines.append(f"    Risk level: {balanced['risk_level']}")
            lines.append(f"    Risk score: {balanced['risk_score']}/10")

        if cheapest:
            lines.append(
                f"  Cheapest eligible option: {cheapest['supplier_name']} - {cheapest['unit_price_usd']} USD/unit"
            )

        if best_quality:
            lines.append(
                f"  Best quality eligible option: {best_quality['supplier_name']} with quality score {best_quality['quality_score']}"
            )

        filtered_options = [
            option
            for option in result["supplier_options"]
            if option["selection_status"] == "not_eligible"
        ]

        if filtered_options:
            lines.append("  Filtered supplier options:")
            for option in filtered_options:
                reasons = option["preference_issues"] or [option["availability_status"]]
                lines.append(
                    f"  - {option['supplier_name']} ({option['country']}): {', '.join(reasons)}"
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
            f"Estimated procurement cost: {plan['procurement_summary']['estimated_total_procurement_cost_usd']} USD. "
            f"Overall procurement risk: {plan['procurement_risk']['overall_risk_level']}."
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
    response["input_resolution"]["input_type"] = "json"
    return response


def run_shopping_agent_from_text(text: str) -> dict[str, Any]:
    request_data = parse_shopping_request_text(text)
    response = run_shopping_agent(request_data)
    response["input_resolution"]["source"] = "natural_language_text"
    response["input_resolution"]["input_type"] = "text"
    return response


def run_shopping_agent_from_any_file(path: str | Path) -> dict[str, Any]:
    path_obj = Path(path)

    if path_obj.suffix.lower() in {".txt", ".md"}:
        request_data = read_shopping_request_text(path_obj)
        response = run_shopping_agent(request_data)
        response["input_resolution"]["source"] = str(path_obj)
        response["input_resolution"]["input_type"] = "text"
        return response

    return run_shopping_agent_from_file(path_obj)
