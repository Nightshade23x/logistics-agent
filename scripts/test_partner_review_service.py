from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_review_service import run_partner_review


def test_partner_review_with_shopping_payload():
    payload = {
        "request_id": "SHOP-TEST-001",
        "customer": "Demo Customer",
        "origin": "India",
        "destination_country": "USA",
        "estimated_total_procurement_cost_usd": 12730.0,
        "selected_items": [
            {
                "product_name": "TVs",
                "category": "electronics",
                "requested_quantity": 50,
                "estimated_total_cost_usd": 10500.0,
            },
            {
                "product_name": "Scooters",
                "category": "mobility",
                "requested_quantity": 5,
                "estimated_total_cost_usd": 1750.0,
            },
        ],
    }

    response = run_partner_review(payload, request_id="TEST-SHOPPING")

    assert response["agent_name"] == "partner_review_service"
    assert response["status"] == "partner_review_not_configured"
    assert response["origin_country"] == "India"
    assert response["destination_country"] == "USA"
    assert response["items_checked"] == 2
    assert response["agent_responses"]["risk_agent"]["agent_name"] == "risk_agent"
    assert len(response["agent_responses"]["compliance_agent"]) == 2
    assert len(response["agent_responses"]["trader_agent"]) == 2
    assert response["agent_responses"]["finance_agent"]["agent_name"] == "finance_agent"


def test_partner_review_with_logistics_payload():
    payload = {
        "shipment_id": "LOG-TEST-001",
        "origin": "India",
        "destination": "USA",
        "total_cbm": 19.41,
        "total_weight_kg": 2250.0,
        "declared_value_usd": 18500.0,
        "items": [
            {
                "name": "Ceramic tiles",
                "category": "building_materials",
                "quantity": 100,
            },
            {
                "name": "TVs",
                "category": "electronics",
                "quantity": 50,
            },
        ],
    }

    response = run_partner_review(payload, request_id="TEST-LOGISTICS")

    assert response["agent_name"] == "partner_review_service"
    assert response["status"] == "partner_review_not_configured"
    assert response["origin_country"] == "India"
    assert response["destination_country"] == "USA"
    assert response["items_checked"] == 2
    assert response["agent_responses"]["finance_agent"]["handoff_payload"]["total_cbm"] == 19.41
    assert response["agent_responses"]["finance_agent"]["handoff_payload"]["total_weight_kg"] == 2250.0


def main() -> None:
    test_partner_review_with_shopping_payload()
    test_partner_review_with_logistics_payload()

    print("All partner review service tests passed.")


if __name__ == "__main__":
    main()
