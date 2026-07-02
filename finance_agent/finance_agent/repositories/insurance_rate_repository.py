"""
Abstract repository for insurance rate lookups.
No concrete data source (DB/API) implemented — stub interface only.
"""

from abc import ABC, abstractmethod


class InsuranceRateRepository(ABC):
    """Provides insurance rate data used to price shipment coverage."""

    @abstractmethod
    def get_rate(self, shipment_id: str) -> float:
        """Return the insurance rate (fraction of declared value) for a shipment."""
        ...