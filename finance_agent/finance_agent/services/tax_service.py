"""
Service responsible for calculating taxes.
"""

from decimal import Decimal

from finance_agent.finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.finance_agent.models.shipment import Shipment


class TaxService(FinanceServiceInterface):
    """
    Calculates tax for a shipment.
    """

    DEFAULT_TAX_RATE = Decimal("0.18")

    def execute(self, shipment: Shipment) -> Decimal:
        """
        Calculate taxes.

        Formula:
            cargo_value × tax_rate
        """
        return shipment.cargo_value * self.DEFAULT_TAX_RATE