"""
Repository responsible for cost data access.
Concrete storage mechanism (DB, file, API) to be decided later.
"""

from abc import abstractmethod

from finance_agent.core.interfaces import RepositoryInterface
from finance_agent.models.cost import Cost


class CostRepository(RepositoryInterface):
    """Handles persistence and retrieval of Cost entities."""

    def get(self, identifier: str) -> Cost:
        """Retrieve a Cost by shipment_id. Implementation pending."""
        ...

    @abstractmethod
    def save(self, entity: Cost) -> Cost:
        """Persist a Cost entity. Implementation pending."""
        ...