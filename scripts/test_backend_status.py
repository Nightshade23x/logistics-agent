from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_status import build_backend_status


ENV_KEYS = [
    "RISK_MCP_SERVER_NAME",
    "COMPLIANCE_MCP_SERVER_NAME",
    "TRADER_MCP_SERVER_NAME",
    "FINANCE_REST_BASE_URL",
]


def _clear_env() -> None:
    for key in ENV_KEYS:
        os.environ.pop(key, None)


def test_backend_status_without_partner_connections():
    _clear_env()

    status = build_backend_status()

    assert status["system_name"] == "logistics_agent_backend"
    assert status["local_demo_ready"] is True
    assert status["live_partner_ready"] is False
    assert status["overall_status"] == "local_demo_ready_partner_connections_missing"
    assert len(status["core_components"]) >= 7
    assert len(status["partner_components"]) == 4
    assert "risk_mcp_server" in status["missing_partner_connections"]
    assert "finance_rest_api" in status["missing_partner_connections"]


def test_backend_status_with_partner_connections():
    _clear_env()

    os.environ["RISK_MCP_SERVER_NAME"] = "risk-server"
    os.environ["COMPLIANCE_MCP_SERVER_NAME"] = "compliance-server"
    os.environ["TRADER_MCP_SERVER_NAME"] = "trader-server"
    os.environ["FINANCE_REST_BASE_URL"] = "http://localhost:9000"

    status = build_backend_status()

    assert status["local_demo_ready"] is True
    assert status["live_partner_ready"] is True
    assert status["overall_status"] == "live_partner_ready"
    assert status["missing_partner_connections"] == []
    assert status["configured_mcp_server_names"]["risk"] == "risk-server"
    assert status["finance_rest_base_url_configured"] is True

    _clear_env()


def main() -> None:
    test_backend_status_without_partner_connections()
    test_backend_status_with_partner_connections()

    print("All backend status tests passed.")


if __name__ == "__main__":
    main()
