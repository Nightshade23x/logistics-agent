"""Tests for RoiService."""

from decimal import Decimal

from finance_agent.finance_agent.services.roi_service import RoiService
from finance_agent.finance_agent.models.finance_report import FinanceReport


def make_report(total_cost: Decimal) -> FinanceReport:
    return FinanceReport(
        shipment_id="TEST001",
        freight_cost=Decimal("0.00"),
        insurance_cost=Decimal("0.00"),
        import_duty=Decimal("0.00"),
        taxes=Decimal("0.00"),
        landed_cost=total_cost,
        currency="USD",
        total_cost=total_cost,
    )


class TestRoiService:
    def test_positive_roi_when_selling_above_cost(self):
        service = RoiService()
        report = make_report(Decimal("1000"))
        roi = service.execute(report, Decimal("1500"))
        assert roi == Decimal("50")  # (1500-1000)/1000 * 100

    def test_negative_roi_when_selling_below_cost(self):
        service = RoiService()
        report = make_report(Decimal("1000"))
        roi = service.execute(report, Decimal("800"))
        assert roi == Decimal("-20")

    def test_zero_total_cost_returns_zero_instead_of_dividing_by_zero(self):
        service = RoiService()
        report = make_report(Decimal("0"))
        roi = service.execute(report, Decimal("500"))
        assert roi == Decimal("0.00")