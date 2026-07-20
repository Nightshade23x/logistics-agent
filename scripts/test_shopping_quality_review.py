from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.shopping_quality_review import build_shopping_quality_review
from app.user_agent import run_user_agent_from_json_file


def test_shopping_quality_review_from_json_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    review = build_shopping_quality_review(response)

    assert review["applicable"] is True
    assert review["selected_items_count"] == 3
    assert review["estimated_total_procurement_cost_usd"] == 12730.0
    assert review["status"] in {"clear", "review_required"}
    assert "blocked" != review["status"]


def test_shopping_quality_review_not_applicable_without_shopping_agent():
    response = {
        "specialist_responses": {}
    }

    review = build_shopping_quality_review(response)

    assert review["applicable"] is False
    assert review["status"] == "not_applicable"


def test_shopping_quality_review_blocks_excluded_country():
    response = {
        "specialist_responses": {
            "shopping_agent": {
                "handoff_payload": {
                    "preferences": {
                        "excluded_countries": ["China"],
                    },
                    "selected_items": [
                        {
                            "product_name": "TVs",
                            "country": "China",
                            "requested_quantity": 10,
                            "available_quantity": 100,
                            "availability_status": "available",
                            "estimated_total_cost_usd": 1000,
                        }
                    ],
                    "estimated_total_procurement_cost_usd": 1000,
                }
            }
        }
    }

    review = build_shopping_quality_review(response)

    assert review["status"] == "blocked"
    assert any("excluded country" in blocker for blocker in review["blockers"])


def test_shopping_quality_review_blocks_budget_exceeded():
    response = {
        "specialist_responses": {
            "shopping_agent": {
                "handoff_payload": {
                    "preferences": {
                        "budget_usd": 500,
                    },
                    "selected_items": [
                        {
                            "product_name": "TVs",
                            "country": "India",
                            "requested_quantity": 10,
                            "available_quantity": 100,
                            "availability_status": "available",
                            "estimated_total_cost_usd": 1000,
                        }
                    ],
                    "estimated_total_procurement_cost_usd": 1000,
                }
            }
        }
    }

    review = build_shopping_quality_review(response)

    assert review["status"] == "blocked"
    assert any("exceeds budget" in blocker for blocker in review["blockers"])


def main() -> None:
    test_shopping_quality_review_from_json_flow()
    test_shopping_quality_review_not_applicable_without_shopping_agent()
    test_shopping_quality_review_blocks_excluded_country()
    test_shopping_quality_review_blocks_budget_exceeded()

    print("All shopping quality review tests passed.")


if __name__ == "__main__":
    main()
