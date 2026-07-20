"""
Core interfaces for the Finance Agent.

Defines the contract other agents (e.g. Logistics Agent) use to
communicate with the Finance Agent, and the contract any concrete
service/repository implementation must follow. No business logic here.
"""

from abc import ABC, abstractmethod
from typing import Any


class AgentInterface(ABC):
    """
    Contract for inter-agent communication.
    Any agent (Finance, Logistics, etc.) exposed to other agents
    should implement this so callers don't depend on internal details.
    """

    @abstractmethod
    def handle_request(self, request: Any) -> Any:
        """Receive a request from another agent and return a response."""
        ...


class FinanceServiceInterface(ABC):
    """
    Contract that all Finance Agent services must implement.
    Routers depend on this, not on concrete service classes.
    """

    @abstractmethod
    def execute(self, request: Any) -> Any:
        """Execute the service's use-case."""
        ...


class RepositoryInterface(ABC):
    """
    Contract that all repositories must implement.
    Services depend on this, not on concrete data-access classes.
    """

    @abstractmethod
    def get(self, identifier: Any) -> Any:
        """Retrieve a single record by identifier."""
        ...

    @abstractmethod
    def save(self, entity: Any) -> Any:
        """Persist a record."""
        ...