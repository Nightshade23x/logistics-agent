from __future__ import annotations

from typing import Any

from app.item_resolver import resolve_items
from app.logistics_agent import build_logistics_plan
from app.report_formatter import format_logistics_plan


def _build_shipment_context(shipment_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "shipment_id": shipment_data.get("shipment_id"),
        "customer": shipment_data.get("customer"),
        "origin": shipment_data.get("origin"),
        "destination": shipment_data.get("destination"),
        "notes": shipment_data.get("notes"),
    }


def _determine_status(
    plan: dict[str, Any] | None,
    unresolved_items: list[dict[str, Any]],
) -> str:
    if plan is None:
        return "needs_more_information"

    if unresolved_items:
        return "partial_plan_needs_more_information"

    risk_level = plan.get("logistics_risk", {}).get("risk_level")
    container_priority = plan.get("container_strategy", {}).get("priority")
    route_priority = plan.get("route_plan", {}).get("priority")

    if "critical" in {risk_level, container_priority, route_priority}:
        return "critical_review_required"

    if "high" in {risk_level, container_priority, route_priority}:
        return "review_required"

    return "ready_for_review"


def _build_summary(plan: dict[str, Any] | None, status: str) -> str:
    if plan is None:
        return "The logistics agent could not create a plan because item dimensions or catalog matches are missing."

    summary = plan["shipment_summary"]
    container = plan["container_recommendation"]

    return (
        f"Logistics plan status: {status}. "
        f"Total cargo is {summary['total_cbm']} CBM and {summary['total_weight_kg']} kg. "
        f"Recommended container: {container['container_name']}."
    )


def _collect_missing_information(
    plan: dict[str, Any] | None,
    unresolved_items: list[dict[str, Any]],
) -> list[str]:
    missing_info: list[str] = []

    for item in unresolved_items:
        missing_info.append(
            f"{item.get('name', 'Unknown item')}: dimensions are missing and no catalog match was found."
        )

    if plan is not None:
        route_missing = plan.get("route_plan", {}).get("missing_info", [])
        missing_info.extend(route_missing)

    return missing_info


def _build_handoff_requests(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if plan is None:
        return []

    handoff_requests: list[dict[str, Any]] = []

    handoff_requests.append(
        {
            "target_agent": "financial_agent",
            "reason": "Estimate freight cost, insurance cost, financial risk, and shipment budget based on CBM, weight, route, and cargo risk.",
            "inputs_needed": [
                "total_cbm",
                "total_weight_kg",
                "container_recommendation",
                "origin",
                "destination",
                "risk_level",
                "cargo_categories",
            ],
        }
    )

    cargo_categories = {
        category
        for item in plan.get("item_breakdown", [])
        for category in item.get("cargo_categories", [])
    }

    if cargo_categories.intersection({"hazardous", "radioactive", "perishable"}):
        handoff_requests.append(
            {
                "target_agent": "compliance_agent",
                "reason": "Check special cargo regulations, documentation, carrier acceptance, and country-specific restrictions.",
                "inputs_needed": [
                    "origin",
                    "destination",
                    "cargo_categories",
                    "container_strategy",
                    "route_plan",
                ],
            }
        )

    return handoff_requests


def run_logistics_agent(shipment_data: dict[str, Any]) -> dict[str, Any]:
    """
    Official entry point for the logistics agent.

    This function is designed so the future multi-agent system can call the
    logistics agent and receive a consistent structured response.
    """
    raw_items = shipment_data.get("items", [])
    shipment_context = _build_shipment_context(shipment_data)

    resolution = resolve_items(raw_items)
    resolved_items = resolution["resolved_items"]
    unresolved_items = resolution["unresolved_items"]

    if not resolved_items:
        status = "needs_more_information"
        summary = _build_summary(None, status)

        return {
            "agent_name": "logistics_agent",
            "status": status,
            "summary": summary,
            "plan": None,
            "report": summary,
            "input_resolution": resolution,
            "missing_information": _collect_missing_information(None, unresolved_items),
            "handoff_requests": [],
        }

    plan = build_logistics_plan(
        resolved_items,
        shipment_context=shipment_context,
    )

    plan["input_resolution"] = {
        "issues": resolution["issues"],
        "unresolved_items": unresolved_items,
    }

    status = _determine_status(plan, unresolved_items)
    summary = _build_summary(plan, status)
    report = format_logistics_plan(plan, shipment_context)

    return {
        "agent_name": "logistics_agent",
        "status": status,
        "summary": summary,
        "plan": plan,
        "report": report,
        "input_resolution": resolution,
        "missing_information": _collect_missing_information(plan, unresolved_items),
        "handoff_requests": _build_handoff_requests(plan),
    }
