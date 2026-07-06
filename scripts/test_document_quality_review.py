from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.document_quality_review import build_document_quality_review
from app.user_agent import run_user_agent_from_files


def test_document_quality_review_from_document_flow():
    response = run_user_agent_from_files(
        [
            ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
            ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
        ]
    )

    review = build_document_quality_review(response)

    assert review["applicable"] is True
    assert review["status"] in {"clear", "review_required", "blocked"}
    assert review["mismatch_count"] == 0
    assert review["status"] != "blocked"


def test_document_quality_review_not_applicable_without_document_agent():
    response = {
        "specialist_responses": {}
    }

    review = build_document_quality_review(response)

    assert review["applicable"] is False
    assert review["status"] == "not_applicable"


def test_document_quality_review_blocks_mismatches():
    response = {
        "specialist_responses": {
            "document_ai_agent": {
                "status": "review_required",
                "summary": "Documents compared with mismatches.",
                "mismatch_count": 2,
                "handoff_payload": {
                    "items": [
                        {"product_name": "TVs", "quantity": 50},
                    ]
                },
            }
        }
    }

    review = build_document_quality_review(response)

    assert review["status"] == "blocked"
    assert review["mismatch_count"] == 2
    assert any("mismatch" in blocker.lower() for blocker in review["blockers"])


def test_document_quality_review_blocks_empty_items():
    response = {
        "specialist_responses": {
            "document_ai_agent": {
                "status": "ready_for_review",
                "summary": "Documents parsed.",
                "handoff_payload": {
                    "items": []
                },
            }
        }
    }

    review = build_document_quality_review(response)

    assert review["status"] == "blocked"
    assert any("No shipment items" in blocker for blocker in review["blockers"])


def main() -> None:
    test_document_quality_review_from_document_flow()
    test_document_quality_review_not_applicable_without_document_agent()
    test_document_quality_review_blocks_mismatches()
    test_document_quality_review_blocks_empty_items()

    print("All document quality review tests passed.")


if __name__ == "__main__":
    main()
