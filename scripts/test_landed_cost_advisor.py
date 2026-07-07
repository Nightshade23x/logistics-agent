from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.landed_cost_advisor import build_landed_cost_advice
from app.user_agent import run_user_agent_from_json_file


def test_landed_cost_advice_from_shopping_json_flow():
    raw_response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    advice = build_landed_cost_advice(raw_response)

    assert advice["applicable"] is True
    assert advice["status"] in {"needs_more_information", "review_required"}
    assert advice["known_inputs"]["procurement_value_usd"] == 12730.0
    assert "freight_quote_usd" in advice["missing_cost_inputs"]
    assert "duty_rate_percent" in advice["missing_cost_inputs"]


def test_landed_cost_advice_in_backend_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert "landed_cost_advice" in payload

    advice = payload["landed_cost_advice"]

    assert advice["applicable"] is True
    assert advice["missing_cost_inputs"]


def test_landed_cost_advice_blocks_without_procurement_value():
    response = {
        "specialist_responses": {
            "logistics_agent": {
                "handoff_payload": {
                    "total_cbm": 10,
                    "total_weight_kg": 1000,
                    "recommended_container": "20ft Standard Container",
                }
            }
        }
    }

    advice = build_landed_cost_advice(response)

    assert advice["status"] == "blocked"
    assert any("Procurement value" in blocker for blocker in advice["blockers"])


def test_landed_cost_advice_clear_with_complete_inputs():
    response = {
        "declared_value_usd": 10000,
        "freight_quote_usd": 1200,
        "insurance_premium_usd": 150,
        "duty_rate_percent": 10,
        "import_tax_rate_percent": 16,
        "customs_brokerage_usd": 250,
        "local_delivery_usd": 300,
        "incoterm": "FOB",
        "origin_country": "India",
        "destination_country": "USA",
        "specialist_responses": {},
    }

    advice = build_landed_cost_advice(response)

    assert advice["status"] == "clear"
    assert advice["missing_cost_inputs"] == []
    assert advice["estimated_subtotal_known_usd"] == 11900


def main() -> None:
    test_landed_cost_advice_from_shopping_json_flow()
    test_landed_cost_advice_in_backend_payload()
    test_landed_cost_advice_blocks_without_procurement_value()
    test_landed_cost_advice_clear_with_complete_inputs()

    print("All landed cost advisor tests passed.")


if __name__ == "__main__":
    main()
