"""
Request/response contracts for insurance cost calculation.
"""

from pydantic import BaseModel


class InsuranceCostRequest(BaseModel):
    """Request to calculate insurance cost for a shipment."""
    shipment_id: str
    declared_value: float
    currency: str


class InsuranceCostResponse(BaseModel):
    """Result of an insurance cost calculation."""
    shipment_id: str
    insurance_cost: float
    currency: str