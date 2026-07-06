from __future__ import annotations

from typing import Any

from app.partner_config import get_partner_integration_config


CORE_COMPONENTS = [
    "user_agent",
    "shopping_agent",
    "document_ai_agent",
    "logistics_agent",
    "partner_review_service",
    "final_verdict",
    "frontend_payload_builder",
]


PARTNER_COMPONENTS = [
    "risk_agent_adapter",
    "compliance_agent_adapter",
    "trader_agent_adapter",
    "finance_agent_adapter",
]


def build_backend_status() -> dict[str, Any]:
    config = get_partner_integration_config()

    local_demo_ready = True
    live_partner_ready = config.is_fully_configured

    if live_partner_ready:
        overall_status = "live_partner_ready"
    elif local_demo_ready:
        overall_status = "local_demo_ready_partner_connections_missing"
    else:
        overall_status = "not_ready"

    return {
        "system_name": "logistics_agent_backend",
        "overall_status": overall_status,
        "local_demo_ready": local_demo_ready,
        "live_partner_ready": live_partner_ready,
        "core_components": [
            {"name": component, "status": "ready"}
            for component in CORE_COMPONENTS
        ],
        "partner_components": [
            {"name": component, "status": "adapter_ready"}
            for component in PARTNER_COMPONENTS
        ],
        "partner_connections": config.configured_connections,
        "missing_partner_connections": config.missing_connections,
        "configured_mcp_server_names": config.mcp_server_names,
        "finance_rest_base_url_configured": bool(config.finance_rest_base_url),
        "recommended_demo_commands": [
            "python scripts/run_all_tests.py",
            "python scripts/system_health_check.py",
            "python scripts/demo_user_agent_summary.py",
            "python scripts/run_frontend_payload.py json data/suppliers/sample_shopping_request.json",
        ],
        "next_backend_steps": [
            "Connect Risk MCP server",
            "Connect Compliance MCP server",
            "Connect Trader MCP server",
            "Connect Finance REST API",
            "Replace adapter placeholders with live service calls once endpoints are available",
        ],
    }
