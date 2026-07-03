from __future__ import annotations

from typing import Any


def _collect_categories(item_breakdown: list[dict[str, Any]]) -> set[str]:
    return {
        category
        for item in item_breakdown
        for category in item.get("cargo_categories", [])
    }


def recommend_route_and_handling(
    origin: str | None,
    destination: str | None,
    item_breakdown: list[dict[str, Any]],
    container_strategy: dict[str, Any],
    logistics_risk: dict[str, Any],
) -> dict[str, Any]:
    """
    Recommends route and handling priorities for the logistics side.

    This does not replace a real carrier/port routing API. It gives operational
    route guidance based on cargo profile and risk.
    """
    categories = _collect_categories(item_breakdown)

    route_type = "standard_ocean_freight"
    priority = "normal"
    route_warnings: list[str] = []
    handling_priorities: list[str] = []
    checkpoints: list[str] = []
    missing_info: list[str] = []

    if "radioactive" in categories:
        route_type = "regulated_specialist_route"
        priority = "critical"
        route_warnings.append(
            "Radioactive cargo requires a specialist approved route and cannot be planned as normal freight."
        )
        handling_priorities.append(
            "Use only approved carriers, approved ports, and specialist handling facilities."
        )

    elif "hazardous" in categories:
        route_type = "dangerous_goods_route"
        priority = "high"
        route_warnings.append(
            "Hazardous cargo may be restricted by carrier, port, route, and documentation rules."
        )
        handling_priorities.append(
            "Confirm dangerous goods acceptance before booking the shipment."
        )

    elif "perishable" in categories:
        route_type = "temperature_sensitive_route"
        priority = "high"
        route_warnings.append(
            "Perishable cargo should avoid long delays, unreliable transshipment points, and temperature breaks."
        )
        handling_priorities.append(
            "Prefer faster routing and temperature-controlled handling."
        )

    if "fragile" in categories:
        handling_priorities.append(
            "Choose a route and carrier with lower handling risk and fewer unnecessary transfers."
        )

    if "heavy" in categories:
        handling_priorities.append(
            "Confirm container payload limits, port lifting capacity, and safe loading equipment."
        )

    if "non_stackable" in categories:
        handling_priorities.append(
            "Avoid route plans that require frequent restuffing or cargo rearrangement."
        )

    if logistics_risk.get("risk_level") in {"high", "critical"}:
        route_warnings.append(
            "Overall logistics risk is high, so routing should be reviewed before booking."
        )

    checkpoints.extend(
        [
            "Confirm final packed dimensions and weight before booking.",
            "Confirm container type and cargo handling requirements.",
            "Confirm pickup location, port of loading, port of discharge, and final delivery point.",
            "Check whether transshipment increases damage, delay, or temperature risk.",
            "Confirm carrier acceptance for the cargo profile.",
        ]
    )

    if not origin:
        missing_info.append("Origin country or loading location is missing.")

    if not destination:
        missing_info.append("Destination country or final delivery location is missing.")

    missing_info.extend(
        [
            "Preferred delivery deadline or maximum transit time.",
            "Port of loading and port of discharge.",
            "Whether door-to-door, port-to-port, or warehouse-to-warehouse service is required.",
            "Whether cargo insurance has already been arranged.",
        ]
    )

    if not route_warnings:
        route_warnings.append(
            "No major route warnings detected from the current cargo profile."
        )

    if not handling_priorities:
        handling_priorities.append(
            "Standard ocean freight handling appears suitable based on current cargo data."
        )

    origin_label = origin or "unknown origin"
    destination_label = destination or "unknown destination"

    return {
        "route_type": route_type,
        "priority": priority,
        "origin": origin_label,
        "destination": destination_label,
        "summary": f"Suggested route profile from {origin_label} to {destination_label}: {route_type}.",
        "route_warnings": route_warnings,
        "handling_priorities": handling_priorities,
        "checkpoints": checkpoints,
        "missing_info": missing_info,
    }
