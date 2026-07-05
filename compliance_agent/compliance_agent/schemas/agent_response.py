"""Shared response envelope matching the multi-agent contract (see docs/agent_contract.md).
Every agent-level tool (as opposed to granular lookup tools) returns this
shape so the future User Agent orchestrator can merge responses uniformly
across MCP and REST agents without per-agent adapters. See
docs/agent_contract.md for details.
"""


from typing import Any, Literal
from pydantic import BaseModel, Field


class HandoffRequest(BaseModel):
    """A request this agent makes for data it needs from another agent."""

    target_agent: str = Field(..., description="e.g. 'compliance_agent', 'logistics_agent'.")
    reason: str = Field(..., description="Why this data is needed.")
    fields_needed: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Standard top-level response contract shared across all agents."""

    agent_name: Literal["compliance_agent"] = "compliance_agent"
    status: Literal["ok", "partial", "error"] = "ok"
    summary: str = Field(..., description="Human-readable one-paragraph summary.")
    plan: list[str] = Field(default_factory=list, description="Steps this agent took.")
    report: dict[str, Any] = Field(default_factory=dict, description="Full structured findings.")
    input_resolution: dict[str, Any] = Field(
        default_factory=dict, description="How input was interpreted."
    )
    missing_information: list[str] = Field(default_factory=list)
    handoff_payload: dict[str, Any] = Field(
        default_factory=dict, description="Data other agents may consume, keyed by field name."
    )
    handoff_requests: list[HandoffRequest] = Field(default_factory=list)
