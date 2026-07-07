from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.procurement_advisor import build_procurement_advice
from app.user_agent import run_user_agent_from_json_file


def test_procurement_advice_from_shopping_json_flow():
    raw_response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    advice = build_procurement_advice(raw_response)

    assert advice["applicable"] is True
    assert advice["selected_items_count"] == 3
    assert advice["estimated_total_procurement_cost_usd"] == 12730.0
    assert advice["negotiation_points"]


def test_procurement_advice_in_backend_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert "procurement_advice" in payload

    advice = payload["procurement_advice"]

    assert advice["applicable"] is True
    assert advice["selected_items_count"] == 3


def test_procurement_advice_not_applicable_without_shopping():
    response = {
        "specialist_responses": {}
    }

    advice = build_procurement_advice(response)

    assert advice["applicable"] is False
    assert advice["status"] == "not_applicable"


def test_procurement_advice_warns_without_backup_suppliers():
    response = {
        "specialist_responses": {
            "shopping_agent": {
                "handoff_payload": {
                    "selected_items": [
                        {
                            "product_name": "TVs",
                            "quantity": 10,
                            "country": "India",
                            "unit_price_usd": 200,
                            "lead_time_days": 20,
                        }
                    ],
                    "estimated_total_procurement_cost_usd": 2000,
                }
            }
        }
    }

    advice = build_procurement_advice(response)

    assert advice["status"] == "review_required"
    assert any("backup" in item.lower() for item in advice["recommendations"])


def main() -> None:
    test_procurement_advice_from_shopping_json_flow()
    test_procurement_advice_in_backend_payload()
    test_procurement_advice_not_applicable_without_shopping()
    test_procurement_advice_warns_without_backup_suppliers()

    print("All procurement advisor tests passed.")


if __name__ == "__main__":
    main()
