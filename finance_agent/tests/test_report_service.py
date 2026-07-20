"""Tests for ReportService — confirms it's no longer a pass-through stub."""

import pytest
from decimal import Decimal

from finance_agent.finance_agent.container import report_service
from finance_agent.finance_agent.models.shipment import Shipment
from finance_agent.finance_agent.models.finance_report import FinanceReport


def make_shipment(**overrides) -> Shipment:
    defaults = dict(
        shipment_id="TEST001",
        origin="China",
        destination="USA",
        weight_kg=500,
        volume_m3=2.5,
        cargo_value=Decimal("10000"),
        currency="USD",
        transport_mode="sea",
        insurance_required=True,
    )
    defaults.update(overrides)
    return Shipment(**defaults)


class TestReportService:
    def test_execute_returns_computed_report_not_the_input(self):
        shipment = make_shipment()
        report = report_service.execute(shipment)

        assert isinstance(report, FinanceReport)
        # Regression guard: the old stub returned the Shipment unchanged.
        assert not isinstance(report, Shipment)
        assert report.total_cost > Decimal("0.00")

    def test_execute_without_selling_price_leaves_profit_at_default(self):
        report = report_service.execute(make_shipment())
        assert report.estimated_profit == Decimal("0.00")

    def test_execute_with_selling_price_computes_profit(self):
        report = report_service.execute(make_shipment(), selling_price=Decimal("15000"))
        expected_profit = Decimal("15000") - report.total_cost
        assert report.estimated_profit == expected_profit