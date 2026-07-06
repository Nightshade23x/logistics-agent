from __future__ import annotations

from typing import Any

from app.partner_adapters.compliance_client import check_product_compliance
from app.partner_adapters.finance_client import calculate_landed_cost
from app.partner_adapters.risk_client import check_country_risk
from app.partner_adapters.trader_client import classify_trade_product
from app.partner_config import get_partner_integration_config
from app.partner_request_builder import build_partner_agent_requests


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("items"), list):
        return payload["items"]

    if isinstance(payload.get("selected_items"), list):
        return payload["selected_items"]

    return []


def _extract_declared_value(payload: dict[str, Any]) -> Any:
    return (
        payload.get("total_value")
        or payload.get("declared_value_usd")
        or payload.get("estimated_total_procurement_cost_usd")
    )


def _iter_agent_responses(agent_responses: dict[str, Any]):
    for response in agent_responses.values():
        if isinstance(response, list):
            for item in response:
                if isinstance(item, dict):
                    yield item
        elif isinstance(response, dict):
            yield response


def _collect_missing_connections(agent_responses: dict[str, Any]) -> list[Any]:
    missing_connections = []

    for response in _iter_agent_responses(agent_responses):
        unverified = response.get("unverified")
        if unverified:
            missing_connections.append(unverified)

    return missing_connections


def _combine_partner_statuses(agent_responses: dict[str, Any]) -> str:
    statuses = [
        response.get("status")
        for response in _iter_agent_responses(agent_responses)
        if response.get("status")
    ]

    if any(status == "blocked" for status in statuses):
        return "blocked"

    if any(status == "error" for status in statuses):
        return "review_required"

    if any(status in {"not_configured", "not_implemented"} for status in statuses):
        return "partner_review_not_configured"

    if any(
        status
        in {
            "critical_review_required",
            "review_required",
            "needs_more_information",
            "partial_plan_needs_more_information",
        }
        for status in statuses
    ):
        return "review_required"

    return "clear"


def run_partner_review(
    payload: dict[str, Any],
    request_id: str | None = None,
    mcp_server_names: dict[str, str] | None = None,
    finance_rest_base_url: str | None = None,
) -> dict[str, Any]:
    config = get_partner_integration_config()

    if mcp_server_names is None:
        mcp_server_names = config.mcp_server_names

    if finance_rest_base_url is None:
        finance_rest_base_url = config.finance_rest_base_url

    partner_requests = build_partner_agent_requests(payload, request_id=request_id)
    payload_validation = partner_requests["payload_validation"]

    origin_country = payload_validation.get("origin")
    destination_country = payload_validation.get("destination")
    items_checked = payload_validation.get("item_count", len(_extract_items(payload)))

    if not partner_requests["is_ready_for_partner_calls"]:
        return {
            "agent_name": "partner_review_service",
            "status": "needs_more_information",
            "summary": "Partner review payload is missing required information.",
            "origin_country": origin_country,
            "destination_country": destination_country,
            "items_checked": items_checked,
            "payload_validation": payload_validation,
            "partner_agent_requests": partner_requests,
            "agent_responses": {},
            "missing_required_fields": payload_validation["errors"],
        }

    agent_responses: dict[str, Any] = {}

    risk_request = partner_requests["risk_agent"]
    agent_responses["risk_agent"] = check_country_risk(
        destination_country=risk_request["destination_country"],
        request_id=risk_request.get("request_id"),
        mcp_server_name=mcp_server_names.get("risk"),
    )

    compliance_responses = []
    for compliance_request in partner_requests["compliance_agent"]:
        compliance_responses.append(
            check_product_compliance(
                product_name=compliance_request["product_name"],
                destination_country=compliance_request["destination_country"],
                origin_country=compliance_request.get("origin_country"),
                product_category=compliance_request.get("product_category"),
                request_id=compliance_request.get("request_id"),
                mcp_server_name=mcp_server_names.get("compliance"),
            )
        )

    agent_responses["compliance_agent"] = compliance_responses

    trader_responses = []
    for trader_request in partner_requests["trader_agent"]:
        trader_responses.append(
            classify_trade_product(
                product_name=trader_request["product_name"],
                origin_country=trader_request["origin_country"],
                destination_country=trader_request["destination_country"],
                product_category=trader_request.get("product_category"),
                declared_value_usd=trader_request.get("declared_value_usd"),
                request_id=trader_request.get("request_id"),
                mcp_server_name=mcp_server_names.get("trader"),
            )
        )

    agent_responses["trader_agent"] = trader_responses

    finance_request = partner_requests["finance_agent"]
    agent_responses["finance_agent"] = calculate_landed_cost(
        origin_country=finance_request["origin_country"],
        destination_country=finance_request["destination_country"],
        total_cbm=finance_request.get("total_cbm"),
        total_weight_kg=finance_request.get("total_weight_kg"),
        declared_value_usd=finance_request.get("declared_value_usd"),
        duty_rate_percent=finance_request.get("duty_rate_percent"),
        selling_price_usd=finance_request.get("selling_price_usd"),
        request_id=finance_request.get("request_id"),
        rest_base_url=finance_rest_base_url,
    )

    missing_connections = _collect_missing_connections(agent_responses)
    status = _combine_partner_statuses(agent_responses)

    return {
        "agent_name": "partner_review_service",
        "status": status,
        "summary": "Partner review service prepared Risk, Compliance, Trader, and Finance checks.",
        "origin_country": origin_country,
        "destination_country": destination_country,
        "items_checked": items_checked,
        "payload_validation": payload_validation,
        "partner_agent_requests": partner_requests,
        "agent_responses": agent_responses,
        "missing_connections": missing_connections,
    }
