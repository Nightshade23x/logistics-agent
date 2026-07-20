from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.compact_frontend_payload import build_compact_frontend_payload


def test_compact_frontend_payload_from_shopping_json_payload():
    full_payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    compact = build_compact_frontend_payload(full_payload)

    assert compact["payload_type"] == "compact_frontend_payload"
    assert compact["executive_summary"]
    assert compact["ui_sections"]
    assert compact["booking_readiness"]
    assert compact["final_answer"]
    assert compact["action_plan"]
    assert compact["debug_counts"]["ui_sections_count"] >= 7


def test_compact_frontend_payload_keeps_key_demo_values():
    full_payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    compact = build_compact_frontend_payload(full_payload)

    assert compact["detected_intent"] == "shopping"
    assert compact["logistics_metrics"]["total_cbm"] == 19.41
    assert compact["logistics_metrics"]["recommended_container"] == "20ft Standard Container"
    assert compact["executive_summary"]["ready_for_first_pass"] is True
    assert compact["executive_summary"]["ready_for_booking"] is False


def test_compact_frontend_payload_does_not_include_raw_specialist_responses():
    full_payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    compact = build_compact_frontend_payload(full_payload)

    assert "specialist_responses" not in compact
    assert "partner_review_payload" not in compact
    assert "raw_response" not in compact


def main() -> None:
    test_compact_frontend_payload_from_shopping_json_payload()
    test_compact_frontend_payload_keeps_key_demo_values()
    test_compact_frontend_payload_does_not_include_raw_specialist_responses()

    print("All compact frontend payload tests passed.")


if __name__ == "__main__":
    main()
