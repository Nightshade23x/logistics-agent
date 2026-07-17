"""Tests for CostEstimationService — the freight/insurance/duty/tax orchestrator."""

import pytest
from decimal import Decimal

from finance_agent.finance_agent.container import cost_estimation_service
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


class TestCostEstimationService:
    def test_returns_finance_report(self):
        report = cost_estimation_service.execute(make_shipment())
        assert isinstance(report, FinanceReport)

    def test_import_duty_is_ten_percent_of_cargo_value(self):
        shipment = make_shipment(cargo_value=Decimal("10000"))
        report = cost_estimation_service.execute(shipment)
        assert report.import_duty == Decimal("1000.00")

    def test_taxes_is_eighteen_percent_of_cargo_value(self):
        shipment = make_shipment(cargo_value=Decimal("10000"))
        report = cost_estimation_service.execute(shipment)
        assert report.taxes == Decimal("1800.00")

    def test_insurance_cost_is_zero_when_not_required(self):
        shipment = make_shipment(insurance_required=False)
        report = cost_estimation_service.execute(shipment)
        assert report.insurance_cost == Decimal("0.00")

    def test_landed_cost_equals_sum_of_components(self):
        report = cost_estimation_service.execute(make_shipment())
        expected = (
            report.freight_cost
            + report.insurance_cost
            + report.import_duty
            + report.taxes
        )
        assert report.landed_cost == expected

    def test_total_cost_equals_landed_cost(self):
        report = cost_estimation_service.execute(make_shipment())
        assert report.total_cost == report.landed_cost

    def test_shipment_id_carries_through(self):
        report = cost_estimation_service.execute(make_shipment(shipment_id="ABC123"))
        assert report.shipment_id == "ABC123"