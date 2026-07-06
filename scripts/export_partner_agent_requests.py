from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_request_builder import build_partner_agent_requests
from app.user_agent import run_user_agent_from_json_file


def main() -> None:
    output_dir = ROOT_DIR / "demo_outputs"
    output_dir.mkdir(exist_ok=True)

    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    partner_payload = response.get("partner_review_payload", {})

    if not partner_payload:
        raise SystemExit("No partner_review_payload found in User Agent response.")

    partner_requests = build_partner_agent_requests(partner_payload)

    output_path = output_dir / "partner_agent_requests.json"
    output_path.write_text(
        json.dumps(partner_requests, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"Exported partner agent requests to: {output_path}")
    print("")
    print("Request summary:")
    print(f"- request_id: {partner_requests.get('request_id')}")
    print(f"- ready_for_partner_calls: {partner_requests.get('is_ready_for_partner_calls')}")
    print(f"- payload_valid: {partner_requests.get('payload_validation', {}).get('is_valid')}")
    print(f"- risk_agent_request: {partner_requests.get('risk_agent') is not None}")
    print(f"- compliance_agent_requests: {len(partner_requests.get('compliance_agent', []))}")
    print(f"- trader_agent_requests: {len(partner_requests.get('trader_agent', []))}")
    print(f"- finance_agent_request: {partner_requests.get('finance_agent') is not None}")


if __name__ == "__main__":
    main()
