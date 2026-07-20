from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.document_requirements_advisor import build_document_requirements_advice
from app.user_agent import run_user_agent_from_json_file


def test_document_requirements_advice_from_shopping_json_flow():
    raw_response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    advice = build_document_requirements_advice(raw_response)

    assert advice["applicable"] is True
    assert "Commercial invoice" in advice["required_documents"]
    assert "Packing list" in advice["required_documents"]
    assert "Bill of lading or airway bill" in advice["required_documents"]
    assert advice["missing_or_unconfirmed_documents"]


def test_document_requirements_advice_in_backend_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert "document_requirements_advice" in payload
    advice = payload["document_requirements_advice"]

    assert advice["applicable"] is True
    assert advice["required_documents"]


def test_document_requirements_advice_flags_battery_documents():
    response = {
        "logistics_quality_review": {
            "special_handling": {
                "detected_special_cases": ["battery_possible"]
            }
        },
        "specialist_responses": {
            "shopping_agent": {
                "handoff_payload": {
                    "selected_items": [
                        {"product_name": "Electric scooters", "quantity": 5}
                    ]
                }
            }
        },
    }

    advice = build_document_requirements_advice(response)

    assert any("UN38.3" in doc for doc in advice["conditional_documents"])
    assert any("battery" in warning.lower() for warning in advice["warnings"])


def main() -> None:
    test_document_requirements_advice_from_shopping_json_flow()
    test_document_requirements_advice_in_backend_payload()
    test_document_requirements_advice_flags_battery_documents()

    print("All document requirements advisor tests passed.")


if __name__ == "__main__":
    main()
