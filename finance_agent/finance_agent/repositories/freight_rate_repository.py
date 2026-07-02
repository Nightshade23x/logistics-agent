"""
Abstract repository for freight rate lookups.
No concrete data source (DB/API) implemented — stub interface only.
"""

from abc import ABC, abstractmethod


class FreightRateRepository(ABC):
    """Provides freight rate data for a given origin/destination pair."""

    @abstractmethod
    def get_rate(self, origin: str, destination: str) -> float:
        """Return the freight rate (currency units per kg) for a route."""
        ...