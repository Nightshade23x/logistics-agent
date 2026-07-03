"""Service that produces a complete FinanceReport for a shipment."""

from typing import Optional
from decimal import Decimal

from finance_agent.finance_agent.models.shipment import Shipment
from finance_agent.finance_agent.models.finance_report import FinanceReport
from finance_agent.finance_agent.services.cost_estimation_service import CostEstimationService
from finance_agent.finance_agent.services.profit_service import ProfitService


class ReportService:
    """Orchestrates a full FinanceReport, optionally including profit."""

    def __init__(
        self,
        cost_estimation_service: CostEstimationService,
        profit_service: ProfitService,
    ) -> None:
        self.cost_estimation_service = cost_estimation_service
        self.profit_service = profit_service

    def execute(self, shipment: Shipment, selling_price: Optional[Decimal] = None) -> FinanceReport:
        report = self.cost_estimation_service.execute(shipment)

        if selling_price is not None:
            report.estimated_profit = self.profit_service.execute(report, selling_price)

        return report