from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.partner_adapters.trade_orchestrator_client import (
    build_trade_orchestrator_query,
    map_orchestrator_status,
    run_trade_orchestrator_review,
)


def test_status_mapping():
    assert map_orchestrator_status("clear") == "ready_for_review"
    assert map_orchestrator_status("review_required") == "review_required"
    assert map_orchestrator_status("blocked") == "blocked"
    assert map_orchestrator_status("something_new") == "review_required"


def test_query_builder_from_structured_payload():
    payload = {
        "origin_country": "India",
        "destination_country": "USA",
        "incoterm": "FOB",
        "total_cbm": 19.41,
        "total_weight_kg": 2250,
        "procurement_value_usd": 12730,
        "currency": "USD",
        "items": [
            {"product_name": "TVs", "quantity": 50},
            {"product_name": "scooters", "quantity": 20},
        ],
    }

    query = build_trade_orchestrator_query(payload)

    assert "ship 50 TVs and 20 scooters" in query
    assert "from India to USA" in query
    assert "incoterm is FOB" in query
    assert "cargo value is 12730 USD" in query
    assert "weight is 2250 kg" in query
    assert "volume is 19.41 m3" in query


def test_run_trade_orchestrator_review_with_fake_http():
    fake_response = {
        "request_id": "REQ-123",
        "parsed_shipment": {
            "product_description": "cotton t-shirt",
            "country_from": "India",
            "country_to": "Japan",
        },
        "compliance_report": {
            "agent_name": "compliance_agent",
            "status": "clear",
            "missing_information": [],
            "handoff_payload": {},
        },
        "trader_report": {
            "agent_name": "trader_agent",
            "status": "clear",
            "missing_information": [],
            "handoff_payload": {
                "hs_code": "6109",
                "duty_rate_percent": 0.0,
                "fta_exists": True,
            },
        },
        "finance_report": {
            "landed_cost": 18000.0,
            "total_cost": 18000.0,
            "currency": "USD",
        },
        "risk_report": {
            "agent_name": "risk_agent",
            "status": "clear",
            "missing_information": [],
            "handoff_payload": {
                "risk_tier": "low",
                "sanctions_status": "clear",
            },
        },
        "agent_errors": {},
        "verdict": {
            "status": "clear",
            "headline": "Shipment looks clear.",
            "blockers": [],
            "warnings": [],
            "next_steps": [],
        },
        "synthesis": "This shipment looks clear.",
    }

    captured = {}

    def fake_http_post(url, payload, timeout_seconds):
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout_seconds"] = timeout_seconds
        return fake_response

    result = run_trade_orchestrator_review(
        {
            "origin_country": "India",
            "destination_country": "Japan",
            "items": [{"product_name": "cotton t-shirts", "quantity": 800}],
        },
        base_url="http://localhost:8010",
        http_post=fake_http_post,
    )

    assert captured["url"] == "http://localhost:8010/orchestrate"
    assert captured["payload"]["query"].startswith("ship 800 cotton t-shirts from India to Japan")
    assert result["agent_name"] == "partner_trade_orchestrator"
    assert result["status"] == "ready_for_review"
    assert result["summary"] == "Shipment looks clear."
    assert result["handoff_payload"]["landed_cost"] == 18000.0
    assert result["handoff_payload"]["hs_code"] == "6109"
    assert result["handoff_payload"]["risk_tier"] == "low"


if __name__ == "__main__":
    test_status_mapping()
    test_query_builder_from_structured_payload()
    test_run_trade_orchestrator_review_with_fake_http()
    print("Trade orchestrator client tests passed.")
