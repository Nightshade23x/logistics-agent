"""Schemas for the orchestrator's input and final output."""

from pydantic import BaseModel, Field


class ShipmentQuery(BaseModel):
    """Free-text input from the user, e.g. 'ship 200 e-bike batteries from China to Brazil'."""

    query: str = Field(..., min_length=1)


class ParsedShipment(BaseModel):
    """Structured fields extracted from free-text by the parser service."""

    product_description: str
    country_from: str
    country_to: str
    target_market: str
    quantity: int | None = None
    cargo_value: float = 0.0
    weight_kg: float = 0.0
    volume_m3: float = 0.0
    currency: str = "USD"