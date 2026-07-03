from __future__ import annotations

from typing import Any

from app.handoff_payload import build_handoff_payload
from app.item_resolver import resolve_items
from app.logistics_agent import build_logistics_plan
from app.report_formatter import format_logistics_plan


def _collect_cargo_categories(plan: dict[str, Any]) -> set[str]:
    categories: set[str] = set()

    for item in plan.get("item_breakdown", []):
        item_categories = item.get("categories", [])
        if isinstance(item_categories, list):
            categories.update(item_categories)

    return categories


def _build_handoff_requests(plan: dict[str, Any]) -> list[dict[str, Any]]:
    categories = _collect_cargo_categories(plan)

    requests = [
        {
            "target_agent": "financial_agent",
            "reason": "Estimate freight cost, insurance cost, financial risk, and shipment budget based on CBM, weight, route, and cargo risk.",
            "inputs_needed": [
                "total_cbm",
                "total_weight_kg",
                "container_recommendation",
                "recommended_load_type",
                "origin",
                "destination",
                "risk_level",
                "cargo_categories",
            ],
        }
    ]

    if categories.intersection({"hazardous", "radioactive", "perishable"}):
        requests.append(
            {
                "target_agent": "compliance_agent",
                "reason": "Check special cargo regulations, documentation, carrier acceptance, and country-specific restrictions.",
                "inputs_needed": [
                    "cargo_categories",
                    "origin",
                    "destination",
                    "item_breakdown",
                    "route_type",
                ],
            }
        )

    return requests


def _determine_status(
    input_resolution: dict[str, Any],
    plan: dict[str, Any],
) -> str:
    unresolved_items = input_resolution.get("unresolved_items", [])

    if unresolved_items:
        return "partial_plan_needs_more_information"

    readiness_status = (
        plan.get("readiness_checklist", {})
        .get("readiness_status", "")
        .lower()
    )

    risk_level = (
        plan.get("logistics_risk", {})
        .get("risk_level", "")
        .lower()
    )

    container_fit_status = (
        plan.get("container_fit", {})
        .get("fit_status", "")
        .lower()
    )

    if readiness_status == "not_ready_blockers_found":
        return "critical_review_required"

    if container_fit_status == "specialist_required":
        return "critical_review_required"

    if risk_level == "critical":
        return "critical_review_required"

    if risk_level in {"high", "moderate"}:
        return "review_required"

    if readiness_status in {
        "specialist_review_required",
        "ready_for_review_with_high_risk",
    }:
        return "review_required"

    return "ready_for_review"


def run_logistics_agent(shipment_data: dict[str, Any]) -> dict[str, Any]:
    raw_items = shipment_data.get("items", [])

    input_resolution = resolve_items(raw_items)

    shipment_context = {
        "shipment_id": shipment_data.get("shipment_id"),
        "customer": shipment_data.get("customer"),
        "origin": shipment_data.get("origin"),
        "destination": shipment_data.get("destination"),
        "notes": shipment_data.get("notes"),
    }

    plan = build_logistics_plan(
        input_resolution["resolved_items"],
        shipment_context=shipment_context,
    )

    report = format_logistics_plan(plan)
    status = _determine_status(input_resolution, plan)
    handoff_payload = build_handoff_payload(plan)
    handoff_requests = _build_handoff_requests(plan)

    missing_information = [
        *input_resolution.get("issues", []),
        *plan.get("route_plan", {}).get("missing_information", []),
    ]

    container_recommendation = plan.get("container_recommendation", {})
    recommended_container = (
        container_recommendation.get("recommended_container")
        or container_recommendation.get("container")
        or container_recommendation.get("container_name")
        or container_recommendation.get("name")
        or container_recommendation.get("selected_container")
        or "Unknown container"
    )

    summary = (
        f"Logistics plan status: {status}. "
        f"Total cargo is {plan['shipment_summary']['total_cbm']} CBM and "
        f"{plan['shipment_summary']['total_weight_kg']} kg. "
        f"Recommended container: "
        f"{recommended_container}."
    )

    return {
        "agent_name": "logistics_agent",
        "status": status,
        "summary": summary,
        "plan": plan,
        "report": report,
        "input_resolution": input_resolution,
        "missing_information": missing_information,
        "handoff_payload": handoff_payload,
        "handoff_requests": handoff_requests,
    }
