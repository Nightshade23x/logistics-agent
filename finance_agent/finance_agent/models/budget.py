"""
Internal domain model representing a budget entity.
Independent of API/schema representation.
"""

from pydantic import BaseModel


class Budget(BaseModel):
    """Domain representation of a budget allocated for an operation."""
    budget_id: str
    total_amount: float
    currency: str