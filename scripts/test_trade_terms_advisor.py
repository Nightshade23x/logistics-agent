from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.trade_terms_advisor import build_trade_terms_advice
from app.user_agent import run_user_agent_from_json_file, run_user_agent_from_text


def test_trade_terms_advice_from_json_flow_missing_incoterm():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    advice = build_trade_terms_advice(response)

    assert advice["applicable"] is True
    assert advice["status"] in {"needs_more_information", "review_required"}
    assert advice["incoterm"] is None
    assert any("incoterm" in question.lower() for question in advice["user_questions"])


def test_trade_terms_advice_detects_fob_from_text_flow():
    request_text = "I need 50 TVs from India to USA under FOB Mumbai terms."
    response = run_user_agent_from_text(request_text)

    advice = build_trade_terms_advice(response, request_text=request_text)

    assert advice["applicable"] is True
    assert advice["incoterm"] == "FOB"
    assert any("handover" in recommendation.lower() for recommendation in advice["recommendations"])


def test_trade_terms_advice_detects_ddp_warning():
    response = {
        "incoterm": "DDP",
        "specialist_responses": {
            "shopping_agent": {
                "handoff_payload": {
                    "origin_country": "India",
                    "destination_country": "USA",
                    "selected_items": [
                        {"product_name": "TVs", "quantity": 10}
                    ],
                }
            }
        }
    }

    advice = build_trade_terms_advice(response)

    assert advice["incoterm"] == "DDP"
    assert advice["status"] == "review_required"
    assert any("highest responsibility" in warning.lower() for warning in advice["warnings"])


def main() -> None:
    test_trade_terms_advice_from_json_flow_missing_incoterm()
    test_trade_terms_advice_detects_fob_from_text_flow()
    test_trade_terms_advice_detects_ddp_warning()

    print("All trade terms advisor tests passed.")


if __name__ == "__main__":
    main()
