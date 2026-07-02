"""
Service responsible for calculating insurance cost.
Single responsibility: insurance cost calculation only.
"""

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.repositories.insurance_rate_repository import InsuranceRateRepository
from finance_agent.schemas.insurance import InsuranceCostRequest, InsuranceCostResponse


class InsuranceCostService(FinanceServiceInterface):
    """Calculates insurance cost for a shipment based on declared value and rate."""

    def __init__(self, insurance_rate_repository: InsuranceRateRepository) -> None:
        self.insurance_rate_repository = insurance_rate_repository

    def execute(self, request: InsuranceCostRequest) -> InsuranceCostResponse:
        """Calculate insurance cost = declared_value * rate(shipment_id)."""
        rate = self.insurance_rate_repository.get_rate(request.shipment_id)
        insurance_cost = request.declared_value * rate
        return InsuranceCostResponse(
            shipment_id=request.shipment_id,
            insurance_cost=insurance_cost,
            currency=request.currency,
        )