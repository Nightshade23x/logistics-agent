"""
Service responsible for calculating landed cost.
"""

from abc import abstractmethod
from decimal import Decimal

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.models.finance_report import FinanceReport


class LandedCostService(FinanceServiceInterface):
    """
    Calculates landed cost.
    """

    @abstractmethod
    def execute(self, report: FinanceReport) -> Decimal:
        """
        Formula:

        Freight
        + Insurance
        + Import Duty
        + Taxes
        """

        return (
            report.freight_cost
            + report.insurance_cost
            + report.import_duty
            + report.taxes
        )