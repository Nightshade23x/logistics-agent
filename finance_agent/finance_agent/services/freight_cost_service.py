"""
Service responsible for calculating freight cost.
Single responsibility: freight cost calculation only.
"""

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.repositories.freight_rate_repository import FreightRateRepository
from finance_agent.schemas.freight import FreightCostRequest, FreightCostResponse


class FreightCostService(FinanceServiceInterface):
    """Calculates freight cost for a shipment based on weight and route rate."""

    def __init__(self, freight_rate_repository: FreightRateRepository) -> None:
        self.freight_rate_repository = freight_rate_repository

    def execute(self, request: FreightCostRequest) -> FreightCostResponse:
        """Calculate freight cost = weight_kg * rate(origin, destination)."""
        rate = self.freight_rate_repository.get_rate(request.origin, request.destination)
        freight_cost = request.weight_kg * rate
        return FreightCostResponse(
            shipment_id=request.shipment_id,
            freight_cost=freight_cost,
            currency=request.currency,
        )