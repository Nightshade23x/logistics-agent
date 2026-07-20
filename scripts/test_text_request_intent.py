from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.text_request_intent import classify_text_request_intent
from app.user_agent import run_user_agent_from_text


def test_text_intent_classifier_detects_shopping_from_quantity_origin_destination():
    text = "I need 50 TVs from India to USA under FOB Mumbai terms."

    assert classify_text_request_intent(text) == "shopping"


def test_text_intent_classifier_detects_shopping_from_supplier_language():
    text = "Find suppliers for 100 ceramic tiles. Prefer India and avoid China."

    assert classify_text_request_intent(text) == "shopping"


def test_text_intent_classifier_detects_logistics_from_shipping_language():
    text = "Ship 20 pallets from India to USA and recommend the best container."

    assert classify_text_request_intent(text) == "logistics"


def test_user_agent_routes_quantity_origin_destination_text_to_shopping():
    response = run_user_agent_from_text(
        "I need 50 TVs from India to USA under FOB Mumbai terms."
    )

    assert response["detected_intent"] == "shopping"
    assert "shopping_agent" in response["agents_called"]


def main() -> None:
    test_text_intent_classifier_detects_shopping_from_quantity_origin_destination()
    test_text_intent_classifier_detects_shopping_from_supplier_language()
    test_text_intent_classifier_detects_logistics_from_shipping_language()
    test_user_agent_routes_quantity_origin_destination_text_to_shopping()

    print("All text request intent tests passed.")


if __name__ == "__main__":
    main()
