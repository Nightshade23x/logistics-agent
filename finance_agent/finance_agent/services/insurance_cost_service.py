"""
Service responsible for calculating insurance cost.
"""

from decimal import Decimal

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.models.shipment import Shipment
from finance_agent.repositories.insurance_rate_repository import InsuranceRateRepository


class InsuranceCostService(FinanceServiceInterface):

    def __init__(self, insurance_rate_repository: InsuranceRateRepository) -> None:
        self.insurance_rate_repository = insurance_rate_repository

    def execute(self, shipment: Shipment) -> Decimal:

        if not shipment.insurance_required:
            return Decimal("0.00")

        rate = self.insurance_rate_repository.get_rate(
            shipment.shipment_id
        )

        return shipment.cargo_value * rate