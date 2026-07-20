from __future__ import annotations

from typing import Any

from app.partner_adapters.base import build_not_configured_response


def classify_trade_product(
    product_name: str,
    origin_country: str,
    destination_country: str,
    product_category: str | None = None,
    declared_value_usd: float | None = None,
    request_id: str | None = None,
    mcp_server_name: str | None = None,
) -> dict[str, Any]:
    if not mcp_server_name:
        response = build_not_configured_response(
            agent_name="trader_agent",
            required_connection="MCP trader server",
        )
        response["handoff_payload"] = {
            "product_name": product_name,
            "product_category": product_category,
            "origin_country": origin_country,
            "destination_country": destination_country,
            "declared_value_usd": declared_value_usd,
            "request_id": request_id,
        }
        return response

    return {
        "agent_name": "trader_agent",
        "status": "not_implemented",
        "summary": "Trader Agent MCP call placeholder. Live MCP call will be added after partner endpoint details are available.",
        "findings": {
            "product_name": product_name,
            "product_category": product_category,
            "origin_country": origin_country,
            "destination_country": destination_country,
            "declared_value_usd": declared_value_usd,
            "mcp_server_name": mcp_server_name,
        },
        "unverified": ["live_mcp_response", "hs_code", "duty_rate"],
        "handoff_payload": {
            "product_name": product_name,
            "product_category": product_category,
            "origin_country": origin_country,
            "destination_country": destination_country,
            "declared_value_usd": declared_value_usd,
            "request_id": request_id,
        },
        "error": None,
    }
