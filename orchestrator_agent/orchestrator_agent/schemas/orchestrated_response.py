"""Final synthesized response returned to the AI interface."""

from typing import Any
from pydantic import BaseModel, Field


class OrchestratedResponse(BaseModel):
    parsed_shipment: dict[str, Any]
    compliance_report: dict[str, Any]
    trader_report: dict[str, Any]
    finance_report: dict[str, Any]
    risk_report: dict[str, Any]
    agent_errors: dict[str, str] = Field(
        default_factory=dict,
        description="Maps agent name to error message for any agent call that failed. "
        "Empty if all four agents succeeded.",
    )
    synthesis: str = Field(..., description="Final human-readable synthesized answer.")