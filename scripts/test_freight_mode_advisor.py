from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.freight_mode_advisor import build_freight_mode_advice
from app.logistics_quality_review import build_logistics_quality_review
from app.user_agent import run_user_agent_from_json_file


def test_freight_mode_advice_from_shopping_json_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    advice = build_freight_mode_advice(response)

    assert advice["applicable"] is True
    assert advice["primary_mode"] == "sea_fcl"
    assert advice["mode_options"]
    assert any(option["mode"] == "sea_fcl" for option in advice["mode_options"])


def test_freight_mode_advice_needs_size_and_weight():
    response = {
        "specialist_responses": {
            "logistics_agent": {
                "handoff_payload": {
                    "recommended_container": "20ft Standard Container"
                }
            }
        }
    }

    advice = build_freight_mode_advice(response)

    assert advice["applicable"] is False
    assert advice["status"] == "needs_more_information"
    assert advice["blockers"]


def test_freight_mode_advice_blocks_invalid_size():
    response = {
        "specialist_responses": {
            "logistics_agent": {
                "handoff_payload": {
                    "total_cbm": 0,
                    "total_weight_kg": 1000,
                    "recommended_container": "20ft Standard Container",
                }
            }
        }
    }

    advice = build_freight_mode_advice(response)

    assert advice["applicable"] is False
    assert advice["status"] == "blocked"


def test_logistics_quality_review_includes_freight_mode_advice():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    review = build_logistics_quality_review(response)

    assert "freight_mode_advice" in review
    assert review["freight_mode_advice"]["applicable"] is True
    assert review["freight_mode_advice"]["primary_mode"] == "sea_fcl"


def main() -> None:
    test_freight_mode_advice_from_shopping_json_flow()
    test_freight_mode_advice_needs_size_and_weight()
    test_freight_mode_advice_blocks_invalid_size()
    test_logistics_quality_review_includes_freight_mode_advice()

    print("All freight mode advisor tests passed.")


if __name__ == "__main__":
    main()
