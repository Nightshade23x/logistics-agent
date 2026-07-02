"""
Service responsible for the cost estimation use-case.
Orchestrates repositories/models. No calculation logic yet.
"""

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.repositories.cost_repository import CostRepository
from finance_agent.schemas.finance_request import CostEstimationRequest
from finance_agent.schemas.finance_response import CostEstimationResponse


class CostEstimationService(FinanceServiceInterface):
    """Handles the 'estimate cost for a shipment' use-case."""

    def __init__(self, cost_repository: CostRepository) -> None:
        self.cost_repository = cost_repository

    def execute(self, request: CostEstimationRequest) -> CostEstimationResponse:
        """Run the cost estimation use-case. Logic to be implemented later."""
        ...