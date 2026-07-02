"""
Abstract repository for currency exchange rate lookups.
No concrete data source (DB/API) implemented — stub interface only.
"""

from abc import ABC, abstractmethod


class ExchangeRateRepository(ABC):
    """Provides exchange rate data between currency pairs."""

    @abstractmethod
    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Return the exchange rate to convert from_currency to to_currency."""
        ...