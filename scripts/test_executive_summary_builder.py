from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.executive_summary_builder import build_executive_summary


def test_executive_summary_from_shopping_json_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    summary = build_executive_summary(payload)

    assert summary["applicable"] is True
    assert summary["ready_for_first_pass"] is True
    assert summary["ready_for_booking"] is False
    assert summary["shipment_snapshot"]["estimated_procurement_cost_usd"] == 12730.0
    assert summary["shipment_snapshot"]["total_cbm"] == 19.41
    assert summary["top_next_actions"]
    assert summary["top_risks"]


def test_executive_summary_in_backend_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert "executive_summary" in payload

    summary = payload["executive_summary"]

    assert summary["applicable"] is True
    assert summary["shipment_snapshot"]["recommended_container"] == "20ft Standard Container"


def test_executive_summary_ready_when_booking_ready():
    payload = {
        "decision": "clear",
        "detected_intent": "shopping",
        "agents_called": ["shopping_agent"],
        "partner_review_status": "clear",
        "booking_readiness": {
            "status": "ready_for_booking_review",
            "ready_for_first_pass": True,
            "ready_for_booking": True,
            "score": 100,
            "next_gate": "booking_review",
            "ready_items": ["All required checks are clear."],
        },
        "logistics_metrics": {},
        "procurement_advice": {},
        "trade_terms_advice": {},
        "landed_cost_advice": {},
        "trade_compliance_readiness": {},
        "final_answer": {},
        "action_plan": {},
    }

    summary = build_executive_summary(payload)

    assert summary["ready_for_booking"] is True
    assert summary["headline"] == "Shipment is ready for booking review."
    assert summary["booking_score"] == 100


def main() -> None:
    test_executive_summary_from_shopping_json_payload()
    test_executive_summary_in_backend_payload()
    test_executive_summary_ready_when_booking_ready()

    print("All executive summary builder tests passed.")


if __name__ == "__main__":
    main()
