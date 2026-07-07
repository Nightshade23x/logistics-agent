from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.insurance_advisor import build_insurance_advice
from app.user_agent import run_user_agent_from_json_file


def test_insurance_advice_from_shopping_json_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    advice = build_insurance_advice(response)

    assert advice["applicable"] is True
    assert advice["status"] in {"review_required", "blocked"}
    assert advice["insurance_recommendation"] in {
        "strongly_recommended",
        "specialist_review_required",
    }
    assert advice["estimated_cargo_value_usd"] == 12730.0
    assert any("insurance" in recommendation.lower() for recommendation in advice["recommendations"])


def test_insurance_advice_warns_when_value_missing():
    response = {
        "specialist_responses": {
            "logistics_agent": {
                "handoff_payload": {
                    "risk_level": "low",
                    "risk_score": 1,
                    "cargo_categories": [],
                }
            }
        }
    }

    advice = build_insurance_advice(response)

    assert advice["applicable"] is True
    assert advice["status"] == "review_required"
    assert advice["estimated_cargo_value_usd"] is None
    assert any("value" in warning.lower() for warning in advice["warnings"])


def test_insurance_advice_blocks_hazardous_cargo():
    response = {
        "specialist_responses": {
            "shopping_agent": {
                "handoff_payload": {
                    "estimated_total_procurement_cost_usd": 5000,
                }
            },
            "logistics_agent": {
                "handoff_payload": {
                    "risk_level": "high",
                    "risk_score": 8,
                    "cargo_categories": ["hazardous"],
                }
            },
        }
    }

    advice = build_insurance_advice(response)

    assert advice["status"] == "blocked"
    assert advice["insurance_recommendation"] == "specialist_review_required"
    assert any("hazardous" in blocker.lower() for blocker in advice["blockers"])


def main() -> None:
    test_insurance_advice_from_shopping_json_flow()
    test_insurance_advice_warns_when_value_missing()
    test_insurance_advice_blocks_hazardous_cargo()

    print("All insurance advisor tests passed.")


if __name__ == "__main__":
    main()
