from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.action_plan_builder import build_action_plan
from app.backend_service import process_json_file_request, process_text_request


def test_action_plan_from_shopping_json_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    action_plan = build_action_plan(payload)

    assert action_plan["status"] in {
        "resolve_blockers",
        "resolve_immediate_actions",
        "review_before_booking",
        "ready_for_first_pass",
    }
    assert action_plan["partner_steps"]
    assert any("Risk MCP" in step for step in action_plan["partner_steps"])
    assert action_plan["before_booking"]


def test_action_plan_from_text_payload_with_missing_destination():
    payload = process_text_request(
        "I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
        "Prefer suppliers from India. Avoid China. Budget 13000 USD."
    )

    action_plan = build_action_plan(payload)

    assert action_plan["user_questions"]
    assert any(
        "destination" in question.lower()
        for question in action_plan["user_questions"]
    )


def test_action_plan_prioritizes_blockers():
    payload = {
        "decision": "blocked",
        "partner_review_status": None,
        "clarification_questions": [],
        "shopping_quality_review": {
            "applicable": True,
            "status": "blocked",
            "blockers": ["Estimated procurement cost exceeds budget."],
            "warnings": [],
            "recommendations": ["Increase budget or reduce quantity."],
        },
        "logistics_quality_review": {"applicable": False},
        "document_quality_review": {"applicable": False},
        "final_answer": {
            "blockers": ["Estimated procurement cost exceeds budget."],
            "warnings": [],
            "next_actions": ["Increase budget or reduce quantity."],
        },
    }

    action_plan = build_action_plan(payload)

    assert action_plan["status"] == "resolve_blockers"
    assert any("budget" in action.lower() for action in action_plan["immediate_actions"])


def main() -> None:
    test_action_plan_from_shopping_json_payload()
    test_action_plan_from_text_payload_with_missing_destination()
    test_action_plan_prioritizes_blockers()

    print("All action plan builder tests passed.")


if __name__ == "__main__":
    main()
