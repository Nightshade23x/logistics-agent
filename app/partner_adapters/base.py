from __future__ import annotations

from typing import Any


def build_partner_agent_response(
    agent_name: str,
    status: str,
    summary: str,
    findings: dict[str, Any] | None = None,
    unverified: list[str] | None = None,
    handoff_payload: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "agent_name": agent_name,
        "status": status,
        "summary": summary,
        "findings": findings or {},
        "unverified": unverified or [],
        "handoff_payload": handoff_payload or {},
        "error": error,
    }


def build_not_configured_response(
    agent_name: str,
    required_connection: str,
) -> dict[str, Any]:
    return build_partner_agent_response(
        agent_name=agent_name,
        status="not_configured",
        summary=f"{agent_name} adapter is ready, but no live {required_connection} connection has been configured yet.",
        findings={},
        unverified=[required_connection],
        handoff_payload={},
    )
