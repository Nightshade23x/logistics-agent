from __future__ import annotations

from typing import Any


def _get_shopping_response(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    specialist_responses = user_agent_response.get("specialist_responses", {})
    shopping_response = specialist_responses.get("shopping_agent", {})

    if isinstance(shopping_response, dict):
        return shopping_response

    return {}


def _get_handoff_payload(shopping_response: dict[str, Any]) -> dict[str, Any]:
    handoff_payload = shopping_response.get("handoff_payload", {})

    if isinstance(handoff_payload, dict):
        return handoff_payload

    return {}


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def build_shopping_quality_review(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    shopping_response = _get_shopping_response(user_agent_response)

    if not shopping_response:
        return {
            "applicable": False,
            "status": "not_applicable",
            "summary": "No Shopping Agent response was found for this request.",
            "selected_items_count": 0,
            "warnings": [],
            "blockers": [],
            "recommendations": [],
        }

    handoff_payload = _get_handoff_payload(shopping_response)
    selected_items = handoff_payload.get("selected_items", [])

    if not isinstance(selected_items, list):
        selected_items = []

    preferences = handoff_payload.get("preferences", {})
    if not isinstance(preferences, dict):
        preferences = {}

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    estimated_total = _as_float(
        handoff_payload.get("estimated_total_procurement_cost_usd")
        or shopping_response.get("estimated_total_procurement_cost_usd")
    )

    budget = _as_float(
        preferences.get("budget_usd")
        or preferences.get("max_budget_usd")
        or handoff_payload.get("budget_usd")
        or handoff_payload.get("max_budget_usd")
    )

    excluded_countries = {
        str(country).strip().lower()
        for country in _as_list(preferences.get("excluded_countries"))
        if str(country).strip()
    }

    preferred_countries = {
        str(country).strip().lower()
        for country in _as_list(preferences.get("preferred_countries"))
        if str(country).strip()
    }

    max_lead_time_days = _as_float(
        preferences.get("max_lead_time_days")
        or preferences.get("maximum_lead_time_days")
    )

    if not selected_items:
        blockers.append("No supplier items were selected.")
        recommendations.append("Ask the user to change quantity, budget, country preference, or product requirements.")

    if budget is not None and estimated_total is not None and estimated_total > budget:
        blockers.append(
            f"Estimated procurement cost {estimated_total} USD exceeds budget {budget} USD."
        )
        recommendations.append("Ask the user whether the budget can increase or whether lower-cost suppliers should be considered.")

    selected_countries = set()

    for item in selected_items:
        if not isinstance(item, dict):
            warnings.append("A selected supplier item is not a dictionary.")
            continue

        product_name = item.get("product_name") or item.get("name") or "Unknown product"
        country = str(item.get("country", "")).strip()
        country_key = country.lower()

        if country_key:
            selected_countries.add(country_key)

        if country_key and country_key in excluded_countries:
            blockers.append(f"{product_name} selected from excluded country: {country}.")

        availability_status = str(item.get("availability_status", "")).lower()
        if availability_status and availability_status != "available":
            blockers.append(f"{product_name} availability is {availability_status}.")

        requested_quantity = _as_float(item.get("requested_quantity") or item.get("quantity"))
        available_quantity = _as_float(item.get("available_quantity"))

        if (
            requested_quantity is not None
            and available_quantity is not None
            and requested_quantity > available_quantity
        ):
            blockers.append(
                f"{product_name} requested quantity {requested_quantity} exceeds available quantity {available_quantity}."
            )

        selection_status = str(item.get("selection_status", "")).lower()
        if selection_status and selection_status not in {"eligible", "selected", "available"}:
            warnings.append(f"{product_name} selection status is {selection_status}.")

        lead_time_days = _as_float(item.get("lead_time_days"))
        if (
            max_lead_time_days is not None
            and lead_time_days is not None
            and lead_time_days > max_lead_time_days
        ):
            warnings.append(
                f"{product_name} lead time {lead_time_days} days exceeds preferred maximum {max_lead_time_days} days."
            )

        item_risk_level = str(item.get("risk_level", "")).lower()
        if item_risk_level in {"high", "critical"}:
            warnings.append(f"{product_name} has {item_risk_level} procurement risk.")

        preference_issues = item.get("preference_issues", [])
        if isinstance(preference_issues, list):
            for issue in preference_issues:
                warnings.append(f"{product_name}: {issue}")

    if preferred_countries and selected_countries:
        if not selected_countries.intersection(preferred_countries):
            warnings.append("No selected supplier is from the preferred country list.")
            recommendations.append("Ask whether non-preferred supplier countries are acceptable.")

    if blockers:
        status = "blocked"
        summary = "Shopping selection has blockers that must be resolved before procurement can continue."
    elif warnings:
        status = "review_required"
        summary = "Shopping selection is usable but should be reviewed before procurement continues."
    else:
        status = "clear"
        summary = "Shopping selection is usable for first-pass procurement planning."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "selected_items_count": len(selected_items),
        "estimated_total_procurement_cost_usd": estimated_total,
        "budget_usd": budget,
        "selected_supplier_countries": sorted(selected_countries),
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
    }
