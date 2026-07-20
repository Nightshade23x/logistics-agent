from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.cargo_special_handling import build_cargo_special_handling_review
from app.logistics_quality_review import build_logistics_quality_review
from app.user_agent import run_user_agent_from_json_file


def test_special_handling_from_shopping_json_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    review = build_cargo_special_handling_review(response)

    assert review["applicable"] is True
    assert review["status"] in {"clear", "review_required", "blocked"}
    assert "fragile_cargo" in review["detected_special_cases"]
    assert any("TVs" in warning or "Ceramic" in warning for warning in review["warnings"])


def test_special_handling_flags_battery_possible():
    response = {
        "specialist_responses": {
            "shopping_agent": {
                "handoff_payload": {
                    "selected_items": [
                        {
                            "product_name": "Electric scooters",
                            "product_category": "electric mobility",
                            "quantity": 5,
                        }
                    ]
                }
            }
        }
    }

    review = build_cargo_special_handling_review(response)

    assert review["status"] == "review_required"
    assert "battery_possible" in review["detected_special_cases"]
    assert any("battery" in warning.lower() for warning in review["warnings"])
    assert any("UN38.3" in recommendation for recommendation in review["recommendations"])


def test_special_handling_blocks_hazardous_cargo():
    response = {
        "specialist_responses": {
            "logistics_agent": {
                "handoff_payload": {
                    "items": [
                        {
                            "product_name": "Flammable paint",
                            "product_category": "hazardous chemical",
                            "quantity": 10,
                        }
                    ]
                }
            }
        }
    }

    review = build_cargo_special_handling_review(response)

    assert review["status"] == "blocked"
    assert "hazardous_cargo" in review["detected_special_cases"]
    assert any("hazardous" in blocker.lower() for blocker in review["blockers"])


def test_logistics_quality_review_includes_special_handling():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    review = build_logistics_quality_review(response)

    assert "special_handling" in review
    assert review["special_handling"]["applicable"] is True
    assert review["special_handling"]["detected_special_cases"]


def main() -> None:
    test_special_handling_from_shopping_json_flow()
    test_special_handling_flags_battery_possible()
    test_special_handling_blocks_hazardous_cargo()
    test_logistics_quality_review_includes_special_handling()

    print("All cargo special handling tests passed.")


if __name__ == "__main__":
    main()
