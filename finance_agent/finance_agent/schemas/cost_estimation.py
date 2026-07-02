"""
Request/response contracts for combined cost estimation.
Supersedes the earlier minimal CostEstimationRequest/Response
in finance_request.py / finance_response.py for this use-case.
"""

from pydantic import BaseModel


class CostEstimationRequest(BaseModel):
    """Request to estimate total cost (freight + insurance) for a shipment."""
    shipment_id: str
    weight_kg: float
    origin: str
    destination: str
    declared_value: float
    currency: str
    target_currency: str


class CostEstimationResponse(BaseModel):
    """Result of a combined cost estimation."""
    shipment_id: str
    freight_cost: float
    insurance_cost: float
    total_cost: float
    currency: str