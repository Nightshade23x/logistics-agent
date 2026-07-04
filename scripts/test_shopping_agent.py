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
        "items": [{"name": "TVs", "quantity": 50}],
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
        "items": [{"name": "Scooters", "quantity": 5}],
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
        "items": [{"name": "Unknown cargo item", "quantity": 10}],
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


def test_preferences_select_india_and_exclude_china():
    request_data = {
        "request_id": "TEST-SHOP-004",
        "customer": "Test Customer",
        "destination_country": "USA",
        "preferences": {
            "preferred_supplier_countries": ["India"],
            "excluded_supplier_countries": ["China"],
            "max_lead_time_days": 20,
            "minimum_quality_score": 8.0,
            "max_budget_usd": 13000,
        },
        "items": [
            {"name": "TVs", "quantity": 50},
            {"name": "Scooters", "quantity": 5},
            {"name": "Ceramic tiles", "quantity": 100},
        ],
    }

    response = run_shopping_agent(request_data)

    assert response["status"] == "ready_for_review"
    assert response["handoff_payload"]["budget_check"]["within_budget"] is True
    assert all(
        item["country"] == "India"
        for item in response["handoff_payload"]["selected_items"]
    )


def test_budget_limit_triggers_review():
    request_data = {
        "request_id": "TEST-SHOP-005",
        "customer": "Test Customer",
        "destination_country": "USA",
        "preferences": {
            "preferred_supplier_countries": ["India"],
            "excluded_supplier_countries": ["China"],
            "max_lead_time_days": 20,
            "minimum_quality_score": 8.0,
            "max_budget_usd": 12000,
        },
        "items": [
            {"name": "TVs", "quantity": 50},
            {"name": "Scooters", "quantity": 5},
            {"name": "Ceramic tiles", "quantity": 100},
        ],
    }

    response = run_shopping_agent(request_data)

    assert response["status"] == "review_required"
    assert response["handoff_payload"]["budget_check"]["within_budget"] is False
    assert "budget" in " ".join(response["missing_information"]).lower()


def test_preferences_can_filter_all_matching_suppliers():
    request_data = {
        "request_id": "TEST-SHOP-006",
        "customer": "Test Customer",
        "destination_country": "USA",
        "preferences": {
            "excluded_supplier_countries": ["India", "Vietnam"],
        },
        "items": [{"name": "TVs", "quantity": 50}],
    }

    response = run_shopping_agent(request_data)

    assert response["status"] in {
        "needs_more_information",
        "partial_plan_needs_more_information",
    }
    assert response["missing_information"]


def main() -> None:
    test_supplier_matching()
    test_build_shopping_plan()
    test_shopping_agent_response_contract()
    test_unknown_product_needs_more_information()
    test_shopping_agent_from_file()
    test_preferences_select_india_and_exclude_china()
    test_budget_limit_triggers_review()
    test_preferences_can_filter_all_matching_suppliers()

    print("All shopping agent tests passed.")


if __name__ == "__main__":
    main()
