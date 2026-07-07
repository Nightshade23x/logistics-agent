from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.trade_compliance_readiness_advisor import build_trade_compliance_readiness
from app.user_agent import run_user_agent_from_json_file


def test_trade_compliance_readiness_from_shopping_json_flow():
    raw_response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    enriched_response = {
        **raw_response,
        "document_requirements_advice": {
            "missing_or_unconfirmed_documents": [
                "Commercial invoice",
                "Packing list",
                "Bill of lading or airway bill",
            ],
            "conditional_documents": [
                "Battery declaration",
                "UN38.3 test summary",
            ],
        },
    }

    advice = build_trade_compliance_readiness(enriched_response)

    assert advice["applicable"] is True
    assert advice["item_count"] == 3
    assert advice["status"] in {"needs_more_information", "review_required"}
    assert any("HS code" in item for item in advice["missing_information"])
    assert any("battery" in item.lower() for item in advice["compliance_flags"])


def test_trade_compliance_readiness_in_backend_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert "trade_compliance_readiness" in payload

    advice = payload["trade_compliance_readiness"]

    assert advice["applicable"] is True
    assert advice["item_count"] == 3
    assert advice["recommendations"]


def test_trade_compliance_readiness_blocks_without_items():
    advice = build_trade_compliance_readiness(
        {
            "specialist_responses": {},
            "trade_terms_advice": {
                "origin_country": "India",
                "destination_country": "USA",
                "incoterm": "FOB",
            },
        }
    )

    assert advice["status"] == "blocked"
    assert advice["ready_for_partner_review"] is False
    assert any("No shipment items" in blocker for blocker in advice["blockers"])


def test_trade_compliance_readiness_clear_with_complete_basic_inputs():
    advice = build_trade_compliance_readiness(
        {
            "partner_review_status": "clear",
            "trade_terms_advice": {
                "origin_country": "India",
                "destination_country": "USA",
                "incoterm": "FOB",
            },
            "specialist_responses": {
                "shopping_agent": {
                    "handoff_payload": {
                        "selected_items": [
                            {
                                "product_name": "Ceramic tiles",
                                "quantity": 100,
                                "hs_code": "6907",
                            }
                        ]
                    }
                }
            },
        }
    )

    assert advice["status"] == "clear"
    assert advice["ready_for_partner_review"] is True


def main() -> None:
    test_trade_compliance_readiness_from_shopping_json_flow()
    test_trade_compliance_readiness_in_backend_payload()
    test_trade_compliance_readiness_blocks_without_items()
    test_trade_compliance_readiness_clear_with_complete_basic_inputs()

    print("All trade compliance readiness advisor tests passed.")


if __name__ == "__main__":
    main()
