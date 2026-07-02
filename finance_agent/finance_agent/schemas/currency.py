"""
Request/response contracts for currency conversion.
"""

from pydantic import BaseModel


class CurrencyConversionRequest(BaseModel):
    """Request to convert an amount between currencies."""
    amount: float
    from_currency: str
    to_currency: str


class CurrencyConversionResponse(BaseModel):
    """Result of a currency conversion."""
    converted_amount: float
    from_currency: str
    to_currency: str