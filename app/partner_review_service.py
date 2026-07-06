from __future__ import annotations

from typing import Any

from app.partner_adapters.compliance_client import check_product_compliance
from app.partner_adapters.finance_client import calculate_landed_cost
from app.partner_adapters.risk_client import check_country_risk
from app.partner_adapters.trader_client import classify_trade_product


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("items"):
        return payload["items"]

    if payload.get("selected_items"):
        return [
            {
                "name": item.get("product_name"),
                "category": item.get("category"),
                "quantity": item.get("requested_quantity"),
                "declared_value_usd": item.get("estimated_total_cost_usd"),
            }
            for item in payload["selected_items"]
        ]

    return []


def _extract_declared_value(payload: dict[str, Any]) -> float | None:
    value = (
        payload.get("total_value")
        or payload.get("declared_value_usd")
        or payload.get("estimated_total_procurement_cost_usd")
    )

    if value is None:
        return None

    return float(value)


def _combine_partner_statuses(responses: list[dict[str, Any]]) -> str:
    statuses = {response.get("status") for response in responses}

    if "blocked" in statuses:
        return "blocked"

    if "error" in statuses:
        return "review_required"

    if "not_configured" in statuses or "not_implemented" in statuses:
        return "partner_review_not_configured"

    if "review_required" in statuses:
        return "review_required"

    return "clear"


def run_partner_review(
    payload: dict[str, Any],
    request_id: str | None = None,
    mcp_server_names: dict[str, str] | None = None,
    finance_rest_base_url: str | None = None,
) -> dict[str, Any]:
    mcp_server_names = mcp_server_names or {}

    origin_country = payload.get("origin_country") or payload.get("origin")
    destination_country = payload.get("destination_country") or payload.get("destination")
    declared_value_usd = _extract_declared_value(payload)
    items = _extract_items(payload)

    agent_responses: dict[str, Any] = {}

    if destination_country:
        agent_responses["risk_agent"] = check_country_risk(
            destination_country=destination_country,
            request_id=request_id,
            mcp_server_name=mcp_server_names.get("risk_agent"),
        )

    compliance_results = []
    trader_results = []

    for item in items:
        product_name = item.get("name") or item.get("product_name")
        product_category = item.get("category") or item.get("cargo_category")
        item_value = item.get("declared_value_usd") or declared_value_usd

        if not product_name or not destination_country:
            continue

        compliance_results.append(
            check_product_compliance(
                product_name=product_name,
                product_category=product_category,
                origin_country=origin_country,
                destination_country=destination_country,
                request_id=request_id,
                mcp_server_name=mcp_server_names.get("compliance_agent"),
            )
        )

        if origin_country:
            trader_results.append(
                classify_trade_product(
                    product_name=product_name,
                    product_category=product_category,
                    origin_country=origin_country,
                    destination_country=destination_country,
                    declared_value_usd=item_value,
                    request_id=request_id,
                    mcp_server_name=mcp_server_names.get("trader_agent"),
                )
            )

    agent_responses["compliance_agent"] = compliance_results
    agent_responses["trader_agent"] = trader_results

    if origin_country and destination_country:
        agent_responses["finance_agent"] = calculate_landed_cost(
            origin_country=origin_country,
            destination_country=destination_country,
            total_cbm=payload.get("total_cbm"),
            total_weight_kg=payload.get("total_weight_kg"),
            declared_value_usd=declared_value_usd,
            duty_rate_percent=payload.get("duty_rate_percent"),
            selling_price_usd=payload.get("selling_price_usd"),
            request_id=request_id,
            rest_base_url=finance_rest_base_url,
        )

    flat_responses = []
    for response in agent_responses.values():
        if isinstance(response, list):
            flat_responses.extend(response)
        else:
            flat_responses.append(response)

    status = _combine_partner_statuses(flat_responses)

    return {
        "agent_name": "partner_review_service",
        "status": status,
        "summary": "Partner review service prepared Risk, Compliance, Trader, and Finance checks.",
        "origin_country": origin_country,
        "destination_country": destination_country,
        "items_checked": len(items),
        "agent_responses": agent_responses,
        "missing_connections": [
            response.get("unverified", [])
            for response in flat_responses
            if response.get("status") in {"not_configured", "not_implemented"}
        ],
    }
