from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_request_builder import build_partner_agent_requests
from app.user_agent import run_user_agent_from_json_file


def test_partner_agent_requests_from_shopping_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    payload = response["partner_review_payload"]
    requests = build_partner_agent_requests(payload)

    assert requests["is_ready_for_partner_calls"] is True
    assert requests["payload_validation"]["is_valid"] is True
    assert requests["request_id"] == "SHOP-REQ-001"

    assert requests["risk_agent"]["destination_country"] == "USA"

    assert len(requests["compliance_agent"]) == 3
    assert requests["compliance_agent"][0]["origin_country"] == "India"
    assert requests["compliance_agent"][0]["destination_country"] == "USA"
    assert requests["compliance_agent"][0]["product_name"] == "TVs"

    assert len(requests["trader_agent"]) == 3
    assert requests["trader_agent"][0]["declared_value_usd"] == 10500.0

    assert requests["finance_agent"]["origin_country"] == "India"
    assert requests["finance_agent"]["destination_country"] == "USA"
    assert requests["finance_agent"]["total_cbm"] == 19.41
    assert requests["finance_agent"]["total_weight_kg"] == 2250.0
    assert requests["finance_agent"]["declared_value_usd"] == 12730.0


def test_partner_agent_requests_invalid_payload():
    payload = {
        "origin": "India",
        "selected_items": [],
    }

    requests = build_partner_agent_requests(payload)

    assert requests["is_ready_for_partner_calls"] is False
    assert requests["payload_validation"]["is_valid"] is False
    assert requests["risk_agent"] is None
    assert requests["compliance_agent"] == []
    assert requests["trader_agent"] == []
    assert requests["finance_agent"] is None


def main() -> None:
    test_partner_agent_requests_from_shopping_flow()
    test_partner_agent_requests_invalid_payload()

    print("All partner request builder tests passed.")


if __name__ == "__main__":
    main()
