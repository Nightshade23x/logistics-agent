from __future__ import annotations

from typing import Any

from app.partner_adapters.base import build_not_configured_response


def check_product_compliance(
    product_name: str,
    destination_country: str,
    origin_country: str | None = None,
    product_category: str | None = None,
    request_id: str | None = None,
    mcp_server_name: str | None = None,
) -> dict[str, Any]:
    if not mcp_server_name:
        response = build_not_configured_response(
            agent_name="compliance_agent",
            required_connection="MCP compliance server",
        )
        response["handoff_payload"] = {
            "product_name": product_name,
            "product_category": product_category,
            "origin_country": origin_country,
            "destination_country": destination_country,
            "request_id": request_id,
        }
        return response

    return {
        "agent_name": "compliance_agent",
        "status": "not_implemented",
        "summary": "Compliance Agent MCP call placeholder. Live MCP call will be added after partner endpoint details are available.",
        "findings": {
            "product_name": product_name,
            "product_category": product_category,
            "origin_country": origin_country,
            "destination_country": destination_country,
            "mcp_server_name": mcp_server_name,
        },
        "unverified": ["live_mcp_response"],
        "handoff_payload": {
            "product_name": product_name,
            "product_category": product_category,
            "origin_country": origin_country,
            "destination_country": destination_country,
            "request_id": request_id,
        },
        "error": None,
    }
