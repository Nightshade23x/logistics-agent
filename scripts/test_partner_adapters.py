from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_adapters.risk_client import check_country_risk
from app.partner_adapters.compliance_client import check_product_compliance
from app.partner_adapters.trader_client import classify_trade_product
from app.partner_adapters.finance_client import calculate_landed_cost


def test_risk_adapter_not_configured():
    response = check_country_risk(
        destination_country="Brazil",
        request_id="TEST-001",
    )

    assert response["agent_name"] == "risk_agent"
    assert response["status"] == "not_configured"
    assert "MCP risk server" in response["unverified"]
    assert response["handoff_payload"]["destination_country"] == "Brazil"


def test_compliance_adapter_not_configured():
    response = check_product_compliance(
        product_name="e-bike batteries",
        product_category="battery",
        origin_country="China",
        destination_country="Brazil",
        request_id="TEST-002",
    )

    assert response["agent_name"] == "compliance_agent"
    assert response["status"] == "not_configured"
    assert "MCP compliance server" in response["unverified"]
    assert response["handoff_payload"]["product_name"] == "e-bike batteries"
    assert response["handoff_payload"]["destination_country"] == "Brazil"


def test_trader_adapter_not_configured():
    response = classify_trade_product(
        product_name="e-bike batteries",
        product_category="battery",
        origin_country="China",
        destination_country="Brazil",
        declared_value_usd=12000.0,
        request_id="TEST-003",
    )

    assert response["agent_name"] == "trader_agent"
    assert response["status"] == "not_configured"
    assert "MCP trader server" in response["unverified"]
    assert response["handoff_payload"]["origin_country"] == "China"
    assert response["handoff_payload"]["declared_value_usd"] == 12000.0


def test_finance_adapter_not_configured():
    response = calculate_landed_cost(
        origin_country="China",
        destination_country="Brazil",
        total_cbm=12.5,
        total_weight_kg=1800.0,
        declared_value_usd=12000.0,
        duty_rate_percent=18.0,
        selling_price_usd=18000.0,
        request_id="TEST-004",
    )

    assert response["agent_name"] == "finance_agent"
    assert response["status"] == "not_configured"
    assert "Finance REST API" in response["unverified"]
    assert response["handoff_payload"]["total_cbm"] == 12.5
    assert response["handoff_payload"]["duty_rate_percent"] == 18.0


def main() -> None:
    test_risk_adapter_not_configured()
    test_compliance_adapter_not_configured()
    test_trader_adapter_not_configured()
    test_finance_adapter_not_configured()

    print("All partner adapter tests passed.")


if __name__ == "__main__":
    main()
