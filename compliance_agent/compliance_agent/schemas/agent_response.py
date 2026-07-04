"""Shared response envelope matching the multi-agent contract (see docs/agent_contract.md)."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class HandoffRequest(BaseModel):
    target_agent: str
    reason: str
    fields_needed: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    agent_name: Literal["compliance_agent"] = "compliance_agent"
    status: Literal["ok", "partial", "error"] = "ok"
    summary: str
    plan: list[str] = Field(default_factory=list)
    report: dict[str, Any] = Field(default_factory=dict)
    input_resolution: dict[str, Any] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    handoff_payload: dict[str, Any] = Field(default_factory=dict)
    handoff_requests: list[HandoffRequest] = Field(default_factory=list)