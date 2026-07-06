from __future__ import annotations

from typing import Any

from app.partner_adapters.base import build_not_configured_response


def check_country_risk(
    destination_country: str,
    request_id: str | None = None,
    mcp_server_name: str | None = None,
) -> dict[str, Any]:
    if not mcp_server_name:
        response = build_not_configured_response(
            agent_name="risk_agent",
            required_connection="MCP risk server",
        )
        response["handoff_payload"] = {
            "destination_country": destination_country,
            "request_id": request_id,
        }
        return response

    return {
        "agent_name": "risk_agent",
        "status": "not_implemented",
        "summary": "Risk Agent MCP call placeholder. Live MCP call will be added after partner endpoint details are available.",
        "findings": {
            "destination_country": destination_country,
            "mcp_server_name": mcp_server_name,
        },
        "unverified": ["live_mcp_response"],
        "handoff_payload": {
            "destination_country": destination_country,
            "request_id": request_id,
        },
        "error": None,
    }
