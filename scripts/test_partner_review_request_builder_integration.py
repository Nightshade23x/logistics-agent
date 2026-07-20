from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_review_service import run_partner_review
from app.user_agent import run_user_agent_from_json_file


def test_partner_review_service_exposes_built_partner_requests():
    user_response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    payload = user_response["partner_review_payload"]
    response = run_partner_review(payload)

    requests = response["partner_agent_requests"]

    assert response["status"] == "partner_review_not_configured"
    assert requests["is_ready_for_partner_calls"] is True
    assert requests["payload_validation"]["is_valid"] is True
    assert requests["risk_agent"]["destination_country"] == "USA"
    assert len(requests["compliance_agent"]) == 3
    assert len(requests["trader_agent"]) == 3
    assert requests["finance_agent"]["origin_country"] == "India"
    assert requests["finance_agent"]["destination_country"] == "USA"
    assert requests["finance_agent"]["total_cbm"] == 19.41


def test_partner_review_service_stops_on_invalid_partner_payload():
    payload = {
        "origin": "India",
        "selected_items": [],
    }

    response = run_partner_review(payload)

    assert response["status"] == "needs_more_information"
    assert response["payload_validation"]["is_valid"] is False
    assert response["partner_agent_requests"]["is_ready_for_partner_calls"] is False
    assert response["agent_responses"] == {}


def main() -> None:
    test_partner_review_service_exposes_built_partner_requests()
    test_partner_review_service_stops_on_invalid_partner_payload()

    print("All partner review request builder integration tests passed.")


if __name__ == "__main__":
    main()
