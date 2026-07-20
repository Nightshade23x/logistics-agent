from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.frontend_payload import build_frontend_payload
from app.user_agent import run_user_agent_from_json_file


def test_frontend_payload_for_shopping_json_flow():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    payload = build_frontend_payload(response)

    assert payload["agent_name"] == "user_agent"
    assert payload["detected_intent"] == "shopping"
    assert payload["decision"] == "review_required"
    assert "shopping_agent" in payload["agents_called"]
    assert "logistics_agent" in payload["agents_called"]
    assert "partner_review_service" in payload["agents_called"]
    assert payload["logistics_metrics"]["total_cbm"] == 19.41
    assert payload["logistics_metrics"]["recommended_container"] == "20ft Standard Container"
    assert payload["partner_review_status"] == "partner_review_not_configured"
    assert payload["missing_information_count"] >= 0
    assert payload["agent_summaries"]
    assert "raw_response" not in payload

    raw_payload = build_frontend_payload(response, include_raw_response=True)
    assert raw_payload["raw_response"]["agent_name"] == "user_agent"


def main() -> None:
    test_frontend_payload_for_shopping_json_flow()

    print("All frontend payload tests passed.")


if __name__ == "__main__":
    main()
