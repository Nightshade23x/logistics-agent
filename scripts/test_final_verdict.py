from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.final_verdict import derive_final_verdict
from app.user_agent import run_user_agent_from_json_file


def test_final_verdict_clear():
    response = {
        "status": "ready_for_review",
        "missing_information": [],
        "specialist_responses": {
            "shopping_agent": {"status": "ready_for_review"},
            "logistics_agent": {"status": "ready_for_review"},
        },
    }

    verdict = derive_final_verdict(response)

    assert verdict["verdict"] == "clear"
    assert verdict["missing_information_count"] == 0


def test_final_verdict_review_required_for_missing_information():
    response = {
        "status": "review_required",
        "missing_information": ["destination_country"],
        "specialist_responses": {
            "logistics_agent": {"status": "review_required"},
        },
    }

    verdict = derive_final_verdict(response)

    assert verdict["verdict"] == "review_required"
    assert verdict["missing_information_count"] == 1


def test_final_verdict_blocked():
    response = {
        "status": "blocked",
        "missing_information": [],
        "specialist_responses": {
            "compliance_agent": {"status": "blocked"},
        },
    }

    verdict = derive_final_verdict(response)

    assert verdict["verdict"] == "blocked"
    assert verdict["blockers"]


def test_user_agent_json_shopping_includes_final_verdict():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert "final_verdict" in response
    assert response["final_verdict"]["verdict"] == "review_required"
    assert response["final_verdict"]["partner_review_status"] == "partner_review_not_configured"
    assert "FINAL VERDICT" in response["final_answer"]


def main() -> None:
    test_final_verdict_clear()
    test_final_verdict_review_required_for_missing_information()
    test_final_verdict_blocked()
    test_user_agent_json_shopping_includes_final_verdict()

    print("All final verdict tests passed.")


if __name__ == "__main__":
    main()
