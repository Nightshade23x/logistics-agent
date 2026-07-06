from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_document_files_request, process_json_file_request
from app.final_answer_builder import build_final_answer


def test_final_answer_builder_from_shopping_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    answer = build_final_answer(payload)

    assert answer["status"] == "review_required"
    assert "first-pass planning" in answer["headline"].lower()
    assert "shopping_agent" in answer["answer_text"]
    assert answer["warnings"]
    assert any(
        "partner" in warning.lower()
        for warning in answer["warnings"] + answer["next_actions"]
    )


def test_final_answer_builder_from_document_payload():
    payload = process_document_files_request(
        [
            ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
            ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
        ]
    )

    answer = build_final_answer(payload)

    assert answer["status"] in {"review_required", "blocked"}
    assert "document_ai_agent" in answer["answer_text"]


def test_final_answer_builder_blocks_when_review_has_blockers():
    payload = {
        "decision": "review_required",
        "detected_intent": "shopping",
        "agents_called": ["shopping_agent"],
        "logistics_metrics": {},
        "shopping_quality_review": {
            "applicable": True,
            "status": "blocked",
            "blockers": ["Estimated procurement cost exceeds budget."],
            "warnings": [],
            "recommendations": ["Increase budget or reduce quantity."],
        },
        "logistics_quality_review": {"applicable": False},
        "document_quality_review": {"applicable": False},
        "partner_review_status": None,
        "clarification_questions": [],
    }

    answer = build_final_answer(payload)

    assert answer["status"] == "blocked"
    assert any("budget" in blocker.lower() for blocker in answer["blockers"])
    assert any("increase budget" in action.lower() for action in answer["next_actions"])


def main() -> None:
    test_final_answer_builder_from_shopping_payload()
    test_final_answer_builder_from_document_payload()
    test_final_answer_builder_blocks_when_review_has_blockers()

    print("All final answer builder tests passed.")


if __name__ == "__main__":
    main()
