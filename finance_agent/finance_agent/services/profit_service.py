"""
Service responsible for estimating profit.
"""

from abc import abstractmethod
from decimal import Decimal

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.models.finance_report import FinanceReport


class ProfitService(FinanceServiceInterface):
    """
    Calculates estimated profit.
    """

    @abstractmethod
    def execute(
        self,
        report: FinanceReport,
        selling_price: Decimal,
    ) -> Decimal:
        """
        Formula:

        Profit = Selling Price - Total Cost
        """

        return selling_price - report.total_cost