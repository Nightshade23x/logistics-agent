"""
Outbound response contracts for the Finance Agent.
Used by routers to shape data sent back to other agents/systems.
No business logic — data shape only.
"""

from pydantic import BaseModel


class FinanceResponse(BaseModel):
    """Base contract for any response returned by the Finance Agent."""
    request_id: str
    success: bool


class CostEstimationResponse(FinanceResponse):
    """Response containing an estimated cost."""
    shipment_id: str
    estimated_cost: float