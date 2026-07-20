"""Service responsible for calculating return on investment."""

from decimal import Decimal
from finance_agent.finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.finance_agent.models.finance_report import FinanceReport


class RoiService(FinanceServiceInterface):
    """Calculates ROI as a percentage of total cost."""

    def execute(self, report: FinanceReport, selling_price: Decimal) -> Decimal:
        """
        Formula:
            ROI (%) = (Selling Price - Total Cost) / Total Cost × 100
        """
        if report.total_cost == 0:
            return Decimal("0.00")
        profit = Decimal(str(selling_price)) - report.total_cost
        return (profit / report.total_cost) * Decimal("100")