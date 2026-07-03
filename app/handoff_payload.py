from __future__ import annotations

from typing import Any


def build_handoff_payload(plan: dict[str, Any]) -> dict[str, Any]:
    """
    Builds a compact structured payload that other agents can consume.
    """
    shipment_summary = plan.get("shipment_summary", {})
    shipment_context = plan.get("shipment_context", {})
    container = plan.get("container_recommendation", {})
    logistics_risk = plan.get("logistics_risk", {})
    container_strategy = plan.get("container_strategy", {})
    route_plan = plan.get("route_plan", {})
    packaging_plan = plan.get("packaging_plan", {})
    readiness = plan.get("readiness_checklist", {})

    cargo_categories = sorted(
        {
            category
            for item in plan.get("item_breakdown", [])
            for category in item.get("cargo_categories", [])
        }
    )

    item_summary = [
        {
            "name": item["name"],
            "quantity": item["quantity"],
            "total_cbm": item["total_cbm"],
            "total_weight_kg": item["total_weight_kg"],
            "categories": item["cargo_categories"],
        }
        for item in plan.get("item_breakdown", [])
    ]

    return {
        "shipment_id": shipment_context.get("shipment_id"),
        "origin": shipment_context.get("origin"),
        "destination": shipment_context.get("destination"),
        "total_items": shipment_summary.get("total_items"),
        "total_cbm": shipment_summary.get("total_cbm"),
        "total_weight_kg": shipment_summary.get("total_weight_kg"),
        "recommended_container": container.get("container_name"),
        "recommended_load_type": plan.get("shipping_load_type", {}).get("recommended_load_type"),
        "container_utilization_percent": container.get("estimated_utilization_percent"),
        "container_options": plan.get("container_options", []),
        "risk_level": logistics_risk.get("risk_level"),
        "risk_score": logistics_risk.get("risk_score"),
        "container_strategy": container_strategy.get("strategy_type"),
        "container_strategy_priority": container_strategy.get("priority"),
        "route_type": route_plan.get("route_type"),
        "route_priority": route_plan.get("priority"),
        "packaging_risk_level": packaging_plan.get("packaging_risk_level"),
        "readiness_status": readiness.get("readiness_status"),
        "cargo_categories": cargo_categories,
        "item_summary": item_summary,
    }
