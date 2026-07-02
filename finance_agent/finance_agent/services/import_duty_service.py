"""
Service responsible for calculating import duty.
"""

from decimal import Decimal

from finance_agent.models.shipment import Shipment
from finance_agent.core.interfaces import FinanceServiceInterface


class ImportDutyService(FinanceServiceInterface):
    """
    Calculates import duty for a shipment.
    """

    DEFAULT_DUTY_RATE = Decimal("0.10")

    def execute(self, shipment: Shipment) -> Decimal:
        """
        Calculate import duty.

        Formula:
            cargo_value × duty_rate
        """
        return shipment.cargo_value * self.DEFAULT_DUTY_RATE