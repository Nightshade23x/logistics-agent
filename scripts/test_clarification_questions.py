from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.clarification_questions import build_clarification_questions
from app.user_agent import run_user_agent_from_text, run_user_agent_from_json_file


def test_clarification_questions_for_text_request_missing_destination():
    response = run_user_agent_from_text(
        "I need 50 TVs, 5 scooters, and 100 ceramic tiles. Prefer suppliers from India. Avoid China. Budget 13000 USD."
    )

    questions = build_clarification_questions(response)

    assert questions
    assert any("destination country" in question.lower() for question in questions)


def test_clarification_questions_for_shopping_json_catalog_estimates():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    questions = build_clarification_questions(response)

    assert any("packed dimensions" in question.lower() for question in questions)


def main() -> None:
    test_clarification_questions_for_text_request_missing_destination()
    test_clarification_questions_for_shopping_json_catalog_estimates()

    print("All clarification question tests passed.")


if __name__ == "__main__":
    main()
