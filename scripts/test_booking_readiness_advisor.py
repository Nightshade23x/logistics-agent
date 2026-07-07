from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.booking_readiness_advisor import build_booking_readiness


def test_booking_readiness_from_shopping_json_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    readiness = build_booking_readiness(payload)

    assert readiness["applicable"] is True
    assert readiness["ready_for_first_pass"] is True
    assert readiness["ready_for_booking"] is False
    assert readiness["status"] in {
        "needs_more_information",
        "review_required",
        "blocked",
    }
    assert readiness["score"] < 100
    assert readiness["next_steps"]


def test_booking_readiness_blocks_when_review_has_blocker():
    payload = {
        "shopping_quality_review": {
            "applicable": True,
            "status": "blocked",
            "blockers": ["Supplier country violates excluded country preference."],
        },
        "logistics_quality_review": {"applicable": False},
        "document_quality_review": {"applicable": False},
        "trade_terms_advice": {"applicable": False},
        "insurance_advice": {"applicable": False},
        "document_requirements_advice": {"applicable": False},
        "landed_cost_advice": {"applicable": False},
        "partner_review_status": None,
        "clarification_questions": [],
    }

    readiness = build_booking_readiness(payload)

    assert readiness["status"] == "blocked"
    assert readiness["ready_for_booking"] is False
    assert any("Supplier country" in blocker for blocker in readiness["blockers"])


def test_booking_readiness_ready_when_all_clear():
    payload = {
        "shopping_quality_review": {"applicable": True, "status": "clear"},
        "logistics_quality_review": {"applicable": True, "status": "clear"},
        "document_quality_review": {"applicable": False},
        "trade_terms_advice": {"applicable": True, "status": "clear"},
        "insurance_advice": {"applicable": True, "status": "clear"},
        "document_requirements_advice": {"applicable": True, "status": "clear"},
        "landed_cost_advice": {"applicable": True, "status": "clear"},
        "partner_review_status": "clear",
        "clarification_questions": [],
    }

    readiness = build_booking_readiness(payload)

    assert readiness["status"] == "ready_for_booking_review"
    assert readiness["ready_for_first_pass"] is True
    assert readiness["ready_for_booking"] is True
    assert readiness["score"] == 100


def main() -> None:
    test_booking_readiness_from_shopping_json_payload()
    test_booking_readiness_blocks_when_review_has_blocker()
    test_booking_readiness_ready_when_all_clear()

    print("All booking readiness advisor tests passed.")


if __name__ == "__main__":
    main()
