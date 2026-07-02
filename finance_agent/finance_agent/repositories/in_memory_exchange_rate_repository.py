from decimal import Decimal

from finance_agent.finance_agent.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)


class InMemoryExchangeRateRepository(ExchangeRateRepository):
    """
    Temporary in-memory exchange rates.
    """

    RATES = {
        ("USD", "INR"): Decimal("83.50"),
        ("INR", "USD"): Decimal("0.0120"),
        ("USD", "EUR"): Decimal("0.92"),
        ("EUR", "USD"): Decimal("1.08"),
    }

    def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        return self.RATES[(from_currency, to_currency)]