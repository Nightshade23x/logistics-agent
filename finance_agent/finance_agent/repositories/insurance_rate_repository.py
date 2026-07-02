"""
Abstract repository for insurance rate lookups.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class InsuranceRateRepository(ABC):
    """Provides insurance rate data."""

    @abstractmethod
    def get_rate(
        self,
        shipment_id: str,
    ) -> Decimal:
        """Return insurance rate."""
        ...