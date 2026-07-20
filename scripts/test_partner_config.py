from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_config import get_partner_integration_config


ENV_KEYS = [
    "RISK_MCP_SERVER_NAME",
    "COMPLIANCE_MCP_SERVER_NAME",
    "TRADER_MCP_SERVER_NAME",
    "FINANCE_REST_BASE_URL",
]


def _clear_env() -> None:
    for key in ENV_KEYS:
        os.environ.pop(key, None)


def test_empty_partner_config():
    _clear_env()

    config = get_partner_integration_config()

    assert config.mcp_server_names == {}
    assert config.finance_rest_base_url is None
    assert not config.is_fully_configured
    assert "risk_mcp_server" in config.missing_connections
    assert "compliance_mcp_server" in config.missing_connections
    assert "trader_mcp_server" in config.missing_connections
    assert "finance_rest_api" in config.missing_connections


def test_configured_partner_config():
    _clear_env()

    os.environ["RISK_MCP_SERVER_NAME"] = "risk-server"
    os.environ["COMPLIANCE_MCP_SERVER_NAME"] = "compliance-server"
    os.environ["TRADER_MCP_SERVER_NAME"] = "trader-server"
    os.environ["FINANCE_REST_BASE_URL"] = "http://localhost:9000"

    config = get_partner_integration_config()

    assert config.mcp_server_names["risk"] == "risk-server"
    assert config.mcp_server_names["compliance"] == "compliance-server"
    assert config.mcp_server_names["trader"] == "trader-server"
    assert config.finance_rest_base_url == "http://localhost:9000"
    assert config.is_fully_configured
    assert config.missing_connections == []

    _clear_env()


def main() -> None:
    test_empty_partner_config()
    test_configured_partner_config()

    print("All partner config tests passed.")


if __name__ == "__main__":
    main()
