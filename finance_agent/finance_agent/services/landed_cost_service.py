"""
Service responsible for calculating landed cost.
"""

from decimal import Decimal

from finance_agent.finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.finance_agent.models.finance_report import FinanceReport


class LandedCostService(FinanceServiceInterface):
    """
    Calculates landed cost.
    """

    def execute(self, report: FinanceReport) -> Decimal:
        return (
            report.freight_cost
            + report.insurance_cost
            + report.import_duty
            + report.taxes
        )