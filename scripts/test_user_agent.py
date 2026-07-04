from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json,
    run_user_agent_from_text,
)


def test_user_agent_routes_shopping_text():
    text = """
    I need 50 TVs, 5 scooters, and 100 ceramic tiles.
    Prefer suppliers from India.
    Avoid China.
    Budget 13000 USD.
    """

    response = run_user_agent_from_text(text)

    assert response["agent_name"] == "user_agent"
    assert response["detected_intent"] == "shopping"
    assert response["agents_called"] == ["shopping_agent"]
    assert response["specialist_response"]["agent_name"] == "shopping_agent"


def test_user_agent_routes_document_files():
    paths = [
        ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
        ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
    ]

    response = run_user_agent_from_files(paths)

    assert response["agent_name"] == "user_agent"
    assert response["detected_intent"] == "document"
    assert response["agents_called"] == ["document_ai_agent", "logistics_agent"]
    assert response["specialist_response"]["agent_name"] == "document_ai_agent"
    assert response["specialist_responses"]["logistics_agent"]["agent_name"] == "logistics_agent"
    assert response["logistics_input"]["origin"] == "India"
    assert response["logistics_input"]["destination"] == "USA"

def test_user_agent_routes_shopping_json():
    data = {
        "request_id": "UA-SHOP-001",
        "customer": "Test Customer",
        "destination_country": "USA",
        "items": [
            {"name": "TVs", "quantity": 50},
        ],
    }

    response = run_user_agent_from_json(data)

    assert response["agent_name"] == "user_agent"
    assert response["detected_intent"] == "shopping"
    assert response["agents_called"] == ["shopping_agent"]


def test_user_agent_routes_logistics_json():
    data = {
        "shipment_id": "UA-LOG-001",
        "customer": "Test Customer",
        "origin": "India",
        "destination": "USA",
        "items": [
            {
                "name": "TVs",
                "quantity": 10,
                "length_cm": 120,
                "width_cm": 20,
                "height_cm": 75,
                "weight_kg": 12,
            }
        ],
    }

    response = run_user_agent_from_json(data)

    assert response["agent_name"] == "user_agent"
    assert response["detected_intent"] == "logistics"
    assert response["agents_called"] == ["logistics_agent"]
    assert response["specialist_response"]["agent_name"] == "logistics_agent"


def test_user_agent_unknown_text():
    response = run_user_agent_from_text("hello can you help me")

    assert response["status"] == "needs_more_information"
    assert response["detected_intent"] == "unknown"


def main() -> None:
    test_user_agent_routes_shopping_text()
    test_user_agent_routes_document_files()
    test_user_agent_routes_shopping_json()
    test_user_agent_routes_logistics_json()
    test_user_agent_unknown_text()

    print("All user agent tests passed.")


if __name__ == "__main__":
    main()
