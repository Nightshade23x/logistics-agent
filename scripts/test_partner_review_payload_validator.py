from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_review_payload_validator import validate_partner_review_payload
from app.user_agent import run_user_agent_from_json_file


def test_valid_partner_review_payload_from_shopping_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    payload = response["partner_review_payload"]
    result = validate_partner_review_payload(payload)

    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["item_count"] == 3
    assert result["origin"] == "India"
    assert result["destination"] == "USA"


def test_invalid_partner_review_payload_missing_destination():
    payload = {
        "origin": "India",
        "selected_items": [
            {
                "product_name": "TVs",
                "category": "electronics",
                "requested_quantity": 50,
                "estimated_total_cost_usd": 10500,
            }
        ],
    }

    result = validate_partner_review_payload(payload)

    assert result["is_valid"] is False
    assert "Missing destination country." in result["errors"]


def test_invalid_partner_review_payload_missing_items():
    payload = {
        "origin": "India",
        "destination": "USA",
    }

    result = validate_partner_review_payload(payload)

    assert result["is_valid"] is False
    assert "Missing item list." in result["errors"]


def main() -> None:
    test_valid_partner_review_payload_from_shopping_flow()
    test_invalid_partner_review_payload_missing_destination()
    test_invalid_partner_review_payload_missing_items()

    print("All partner review payload validator tests passed.")


if __name__ == "__main__":
    main()
