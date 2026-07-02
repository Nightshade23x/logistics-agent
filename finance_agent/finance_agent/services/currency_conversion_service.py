"""
Service responsible for currency conversion.
Single responsibility: currency conversion only.
"""

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.repositories.exchange_rate_repository import ExchangeRateRepository
from finance_agent.schemas.currency import CurrencyConversionRequest, CurrencyConversionResponse


class CurrencyConversionService(FinanceServiceInterface):
    """Converts an amount from one currency to another using exchange rate data."""

    def __init__(self, exchange_rate_repository: ExchangeRateRepository) -> None:
        self.exchange_rate_repository = exchange_rate_repository

    def execute(self, request: CurrencyConversionRequest) -> CurrencyConversionResponse:
        """Calculate converted_amount = amount * rate(from_currency, to_currency)."""
        rate = self.exchange_rate_repository.get_rate(request.from_currency, request.to_currency)
        converted_amount = request.amount * rate
        return CurrencyConversionResponse(
            converted_amount=converted_amount,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
        )