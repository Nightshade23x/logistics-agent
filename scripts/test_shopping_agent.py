from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.shopping_agent import build_shopping_plan, find_supplier_matches, load_supplier_catalog
from app.shopping_service import run_shopping_agent, run_shopping_agent_from_file


def test_supplier_matching():
    catalog = load_supplier_catalog()
    matches = find_supplier_matches("TVs", catalog)

    assert len(matches) >= 1
    assert matches[0]["product_name"] == "TVs"


def test_build_shopping_plan():
    request_data = {
        "request_id": "TEST-SHOP-001",
        "customer": "Test Customer",
        "destination_country": "USA",
        "items": [
            {
                "name": "TVs",
                "quantity": 50,
            }
        ],
    }

    plan = build_shopping_plan(request_data)

    assert plan["status"] == "ready_for_review"
    assert plan["procurement_summary"]["estimated_total_procurement_cost_usd"] > 0
    assert len(plan["selected_items"]) == 1


def test_shopping_agent_response_contract():
    request_data = {
        "request_id": "TEST-SHOP-002",
        "customer": "Test Customer",
        "destination_country": "USA",
        "items": [
            {
                "name": "Scooters",
                "quantity": 5,
            }
        ],
    }

    response = run_shopping_agent(request_data)

    assert response["agent_name"] == "shopping_agent"
    assert "status" in response
    assert "summary" in response
    assert "plan" in response
    assert "report" in response
    assert "handoff_payload" in response
    assert "handoff_requests" in response
    assert response["handoff_payload"]["estimated_total_procurement_cost_usd"] > 0


def test_unknown_product_needs_more_information():
    request_data = {
        "request_id": "TEST-SHOP-003",
        "customer": "Test Customer",
        "destination_country": "USA",
        "items": [
            {
                "name": "Unknown cargo item",
                "quantity": 10,
            }
        ],
    }

    response = run_shopping_agent(request_data)

    assert response["status"] in {
        "needs_more_information",
        "partial_plan_needs_more_information",
    }
    assert response["missing_information"]


def test_shopping_agent_from_file():
    path = ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"

    response = run_shopping_agent_from_file(path)

    assert response["agent_name"] == "shopping_agent"
    assert response["status"] == "ready_for_review"
    assert len(response["handoff_payload"]["selected_items"]) >= 1


def main() -> None:
    test_supplier_matching()
    test_build_shopping_plan()
    test_shopping_agent_response_contract()
    test_unknown_product_needs_more_information()
    test_shopping_agent_from_file()

    print("All shopping agent tests passed.")


if __name__ == "__main__":
    main()
