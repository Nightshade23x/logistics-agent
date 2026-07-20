from __future__ import annotations

from typing import Any


def _collect_categories(item_breakdown: list[dict[str, Any]]) -> set[str]:
    return {
        category
        for item in item_breakdown
        for category in item.get("cargo_categories", [])
    }


def generate_readiness_checklist(
    shipment_context: dict[str, Any],
    item_breakdown: list[dict[str, Any]],
    container_recommendation: dict[str, Any],
    container_strategy: dict[str, Any],
    logistics_risk: dict[str, Any],
    route_plan: dict[str, Any],
    packaging_plan: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a practical shipment readiness checklist for the logistics agent.
    """
    categories = _collect_categories(item_breakdown)
    blocking_items: list[str] = []

    origin = shipment_context.get("origin")
    destination = shipment_context.get("destination")

    if not origin:
        blocking_items.append("Origin country or loading location is missing.")

    if not destination:
        blocking_items.append("Destination country or final delivery location is missing.")

    if container_recommendation["container_name"] == "Multiple containers or specialist planning required":
        blocking_items.append(
            "Container plan is not final because the shipment exceeds standard safe planning limits."
        )

    if "radioactive" in categories:
        blocking_items.append(
            "Radioactive cargo requires specialist approval before normal shipment planning."
        )

    if "hazardous" in categories:
        blocking_items.append(
            "Hazardous cargo classification and carrier acceptance must be confirmed before booking."
        )

    before_booking = [
        "Confirm final packed length, width, height, and weight for every cargo item.",
        "Confirm total CBM and total shipment weight after packaging.",
        "Confirm container type and whether one container is enough.",
        "Confirm pickup location, port of loading, port of discharge, and final delivery location.",
        "Confirm required delivery date or maximum acceptable transit time.",
        "Confirm whether cargo insurance is required before booking.",
    ]

    before_loading = [
        "Inspect packaging condition before cargo enters the container.",
        "Check that fragile, heavy, non-stackable, or special-handling labels are visible.",
        "Load heavy cargo first and distribute weight evenly across the floor.",
        "Keep fragile cargo separated from heavy cargo and protect it with cushioning.",
        "Reserve floor space for non-stackable cargo.",
        "Use straps, blocking, chocks, or dunnage to prevent cargo movement.",
    ]

    before_dispatch = [
        "Photograph cargo before loading, during loading, and after final container stuffing.",
        "Record container number and seal number.",
        "Confirm that the final loaded container matches the planned loading sequence.",
        "Confirm that all operational warnings have been reviewed.",
        "Share final CBM, weight, route, and risk information with the financial agent.",
    ]

    if "perishable" in categories:
        before_booking.append(
            "Confirm temperature range, reefer availability, and maximum transit time for perishable cargo."
        )
        before_dispatch.append(
            "Confirm temperature-control settings and monitoring method before dispatch."
        )

    if "hazardous" in categories:
        before_booking.append(
            "Confirm dangerous goods classification, packaging, labelling, and carrier acceptance."
        )

    if "radioactive" in categories:
        before_booking.append(
            "Stop normal booking flow and use specialist radioactive-cargo approval process."
        )

    handoff_checks = [
        "Send total CBM, total weight, recommended container, and risk level to the financial agent.",
        "Send cargo categories and route profile to the compliance agent if restricted cargo is present.",
    ]

    risk_level = logistics_risk.get("risk_level")
    container_priority = container_strategy.get("priority")
    route_priority = route_plan.get("priority")
    packaging_risk = packaging_plan.get("packaging_risk_level")

    if blocking_items:
        readiness_status = "not_ready_blockers_found"
    elif "critical" in {risk_level, container_priority, route_priority, packaging_risk}:
        readiness_status = "specialist_review_required"
    elif "high" in {risk_level, container_priority, route_priority, packaging_risk}:
        readiness_status = "ready_for_review_with_high_risk"
    else:
        readiness_status = "ready_for_standard_review"

    return {
        "readiness_status": readiness_status,
        "blocking_items": blocking_items,
        "sections": [
            {
                "title": "Before booking",
                "items": before_booking,
            },
            {
                "title": "Before loading",
                "items": before_loading,
            },
            {
                "title": "Before dispatch",
                "items": before_dispatch,
            },
            {
                "title": "Agent handoff checks",
                "items": handoff_checks,
            },
        ],
    }
