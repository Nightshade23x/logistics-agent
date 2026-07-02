"""
Internal domain model representing a cost entity.
Independent of API/schema representation.
"""

from pydantic import BaseModel


class Cost(BaseModel):
    """Domain representation of a cost associated with a shipment."""
    shipment_id: str
    amount: float
    currency: str