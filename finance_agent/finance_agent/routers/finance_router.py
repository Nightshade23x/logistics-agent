"""
Router: entry point for other agents/systems to reach the Finance Agent.
Delegates to services. No business logic.
"""

from finance_agent.core.interfaces import AgentInterface
from finance_agent.schemas.finance_request import CostEstimationRequest
from finance_agent.schemas.finance_response import CostEstimationResponse
from finance_agent.services.cost_estimation_service import CostEstimationService


class FinanceRouter(AgentInterface):
    """Routes inbound requests to the appropriate Finance Agent service."""

    def __init__(self, cost_estimation_service: CostEstimationService) -> None:
        self.cost_estimation_service = cost_estimation_service

    def handle_request(self, request: CostEstimationRequest) -> CostEstimationResponse:
        """Entry point other agents call. Delegates to a service."""
        return self.cost_estimation_service.execute(request)