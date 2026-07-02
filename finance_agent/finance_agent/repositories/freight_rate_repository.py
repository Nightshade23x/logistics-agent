"""
Abstract repository for freight rate lookups.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class FreightRateRepository(ABC):
    """Provides freight rate data for a given origin/destination pair."""

    @abstractmethod
    def get_rate(
        self,
        origin: str,
        destination: str,
    ) -> Decimal:
        """Return freight rate."""
        ...