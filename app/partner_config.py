from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PartnerIntegrationConfig:
    risk_mcp_server_name: str | None = None
    compliance_mcp_server_name: str | None = None
    trader_mcp_server_name: str | None = None
    finance_rest_base_url: str | None = None

    @property
    def mcp_server_names(self) -> dict[str, str]:
        names: dict[str, str] = {}

        if self.risk_mcp_server_name:
            names["risk"] = self.risk_mcp_server_name

        if self.compliance_mcp_server_name:
            names["compliance"] = self.compliance_mcp_server_name

        if self.trader_mcp_server_name:
            names["trader"] = self.trader_mcp_server_name

        return names

    @property
    def configured_connections(self) -> dict[str, bool]:
        return {
            "risk_mcp_server": bool(self.risk_mcp_server_name),
            "compliance_mcp_server": bool(self.compliance_mcp_server_name),
            "trader_mcp_server": bool(self.trader_mcp_server_name),
            "finance_rest_api": bool(self.finance_rest_base_url),
        }

    @property
    def missing_connections(self) -> list[str]:
        missing = []

        for connection_name, is_configured in self.configured_connections.items():
            if not is_configured:
                missing.append(connection_name)

        return missing

    @property
    def is_fully_configured(self) -> bool:
        return not self.missing_connections


def _clean_env_value(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    return cleaned


def get_partner_integration_config() -> PartnerIntegrationConfig:
    return PartnerIntegrationConfig(
        risk_mcp_server_name=_clean_env_value(os.getenv("RISK_MCP_SERVER_NAME")),
        compliance_mcp_server_name=_clean_env_value(os.getenv("COMPLIANCE_MCP_SERVER_NAME")),
        trader_mcp_server_name=_clean_env_value(os.getenv("TRADER_MCP_SERVER_NAME")),
        finance_rest_base_url=_clean_env_value(os.getenv("FINANCE_REST_BASE_URL")),
    )
