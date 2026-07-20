"""
Service responsible for calculating freight cost.
"""

from decimal import Decimal

from finance_agent.finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.finance_agent.models.shipment import Shipment
from finance_agent.finance_agent.repositories.freight_rate_repository import FreightRateRepository


class FreightCostService(FinanceServiceInterface):

    def __init__(self, freight_rate_repository: FreightRateRepository) -> None:
        self.freight_rate_repository = freight_rate_repository

    def execute(self, shipment: Shipment) -> Decimal:

        rate = self.freight_rate_repository.get_rate(
            shipment.origin,
            shipment.destination,
        )

        return Decimal(str(shipment.weight_kg)) * rate