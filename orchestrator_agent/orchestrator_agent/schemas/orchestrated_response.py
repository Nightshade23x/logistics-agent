"""Final synthesized response returned to the AI interface."""

from typing import Any
from pydantic import BaseModel, Field
from typing import Any, Literal

class Verdict(BaseModel):
    status: Literal["clear", "review_required", "blocked"] = Field(
        ..., description="Overall shipment verdict."
    )
    headline: str = Field(..., description="One-sentence summary of the verdict.")
    blockers: list[str] = Field(default_factory=list, description="Must-fix issues before shipping.")
    warnings: list[str] = Field(default_factory=list, description="Review-recommended issues.")
    next_steps: list[str] = Field(default_factory=list, description="Concrete recommended actions.")

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
    verdict: Verdict

    synthesis: str = Field(..., description="Final human-readable synthesized answer.")