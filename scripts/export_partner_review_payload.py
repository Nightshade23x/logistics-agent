from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

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

    output_path = output_dir / "partner_review_payload.json"
    output_path.write_text(
        json.dumps(partner_payload, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"Exported partner review payload to: {output_path}")
    print("")
    print("Payload summary:")
    print(f"- request_id: {partner_payload.get('request_id')}")
    print(f"- origin: {partner_payload.get('origin')}")
    print(f"- destination: {partner_payload.get('destination')}")
    print(f"- total_cbm: {partner_payload.get('total_cbm')}")
    print(f"- total_weight_kg: {partner_payload.get('total_weight_kg')}")
    print(f"- declared_value_usd: {partner_payload.get('declared_value_usd')}")
    print(f"- selected_items: {len(partner_payload.get('selected_items', []))}")


if __name__ == "__main__":
    main()
