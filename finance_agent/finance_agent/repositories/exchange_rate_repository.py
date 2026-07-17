"""
Abstract repository for exchange rate lookups.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class ExchangeRateRepository(ABC):
    """Provides exchange rate data."""

    @abstractmethod
    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """Return exchange rate."""
        ...