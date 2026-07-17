"""
Inbound request contracts for the Finance Agent.
Used by routers to validate data coming from other agents/systems.
No business logic — data shape only.
"""

from pydantic import BaseModel


class FinanceRequest(BaseModel):
    """Base contract for any request sent to the Finance Agent."""
    request_id: str
    source_agent: str


class CostEstimationRequest(FinanceRequest):
    """Request to estimate cost for a shipment or operation."""
    shipment_id: str