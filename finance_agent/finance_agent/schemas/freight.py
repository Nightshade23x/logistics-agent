"""
Request/response contracts for freight cost calculation.
"""

from pydantic import BaseModel


class FreightCostRequest(BaseModel):
    """Request to calculate freight cost for a shipment."""
    shipment_id: str
    weight_kg: float
    origin: str
    destination: str
    currency: str


class FreightCostResponse(BaseModel):
    """Result of a freight cost calculation."""
    shipment_id: str
    freight_cost: float
    currency: str