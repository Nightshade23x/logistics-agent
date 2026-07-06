from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.logistics_quality_review import build_logistics_quality_review
from app.user_agent import run_user_agent_from_json_file


def test_logistics_quality_review_from_shopping_json_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    review = build_logistics_quality_review(response)

    assert review["applicable"] is True
    assert review["total_cbm"] == 19.41
    assert review["total_weight_kg"] == 2250.0
    assert review["recommended_container"] == "20ft Standard Container"
    assert review["status"] in {"clear", "review_required", "blocked"}
    assert review["status"] == "review_required"
    assert any("fragile" in warning.lower() or "risk" in warning.lower() for warning in review["warnings"])


def test_logistics_quality_review_not_applicable_without_logistics_agent():
    response = {
        "specialist_responses": {}
    }

    review = build_logistics_quality_review(response)

    assert review["applicable"] is False
    assert review["status"] == "not_applicable"


def test_logistics_quality_review_blocks_missing_container():
    response = {
        "specialist_responses": {
            "logistics_agent": {
                "status": "review_required",
                "summary": "Test logistics response.",
                "handoff_payload": {
                    "total_cbm": 10,
                    "total_weight_kg": 1000,
                    "risk_level": "low",
                    "cargo_categories": [],
                },
            }
        }
    }

    review = build_logistics_quality_review(response)

    assert review["status"] == "blocked"
    assert any("No recommended container" in blocker for blocker in review["blockers"])


def test_logistics_quality_review_blocks_hazardous_cargo():
    response = {
        "specialist_responses": {
            "logistics_agent": {
                "status": "review_required",
                "summary": "Test logistics response.",
                "handoff_payload": {
                    "total_cbm": 10,
                    "total_weight_kg": 1000,
                    "recommended_container": "20ft Standard Container",
                    "risk_level": "high",
                    "cargo_categories": ["hazardous"],
                },
            }
        }
    }

    review = build_logistics_quality_review(response)

    assert review["status"] == "blocked"
    assert any("hazardous" in blocker.lower() for blocker in review["blockers"])


def main() -> None:
    test_logistics_quality_review_from_shopping_json_flow()
    test_logistics_quality_review_not_applicable_without_logistics_agent()
    test_logistics_quality_review_blocks_missing_container()
    test_logistics_quality_review_blocks_hazardous_cargo()

    print("All logistics quality review tests passed.")


if __name__ == "__main__":
    main()
