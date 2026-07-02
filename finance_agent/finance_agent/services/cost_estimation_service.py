"""
Finance Orchestrator Service.

Coordinates all finance services and produces a FinanceReport.
"""

from abc import abstractmethod
from decimal import Decimal

from finance_agent.finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.finance_agent.models.finance_report import FinanceReport
from finance_agent.finance_agent.models.shipment import Shipment
from finance_agent.finance_agent.services.freight_cost_service import FreightCostService
from finance_agent.finance_agent.services.insurance_cost_service import InsuranceCostService
from finance_agent.finance_agent.services.import_duty_service import ImportDutyService
from finance_agent.finance_agent.services.tax_service import TaxService
from finance_agent.finance_agent.services.landed_cost_service import LandedCostService


class CostEstimationService(FinanceServiceInterface):
    """
    Orchestrates all finance calculations.
    """

    def __init__(
        self,
        freight_service: FreightCostService,
        insurance_service: InsuranceCostService,
        import_duty_service: ImportDutyService,
        tax_service: TaxService,
        landed_cost_service: LandedCostService,
    ) -> None:

        self.freight_service = freight_service
        self.insurance_service = insurance_service
        self.import_duty_service = import_duty_service
        self.tax_service = tax_service
        self.landed_cost_service = landed_cost_service

    @abstractmethod
    def execute(self, shipment: Shipment) -> FinanceReport:

        freight = self.freight_service.execute(shipment)
        insurance = self.insurance_service.execute(shipment)
        duty = self.import_duty_service.execute(shipment)
        taxes = self.tax_service.execute(shipment)

        report = FinanceReport(
            shipment_id=shipment.shipment_id,
            freight_cost=freight,
            insurance_cost=insurance,
            import_duty=duty,
            taxes=taxes,
            landed_cost=Decimal("0.00"),
            currency=shipment.currency,
            total_cost=Decimal("0.00"),
        )

        landed_cost = self.landed_cost_service.execute(report)

        report.landed_cost = landed_cost
        report.total_cost = landed_cost

        return report