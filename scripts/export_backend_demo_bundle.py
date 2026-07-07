from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.compact_frontend_payload import build_compact_frontend_payload
from app.backend_service import process_json_file_request
from app.backend_status import build_backend_status
from app.partner_request_builder import build_partner_agent_requests


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> None:
    output_dir = ROOT_DIR / "demo_outputs"
    output_dir.mkdir(exist_ok=True)

    frontend_payload_with_raw = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json",
        include_raw_response=True,
    )

    raw_response = frontend_payload_with_raw.get("raw_response", {})

    frontend_payload = dict(frontend_payload_with_raw)
    frontend_payload.pop("raw_response", None)

    partner_review_payload = raw_response.get("partner_review_payload", {})
    partner_agent_requests = build_partner_agent_requests(partner_review_payload)
    backend_status = build_backend_status()

    outputs = {
        "backend_status.json": backend_status,
        "frontend_payload_shopping.json": frontend_payload,
        "partner_review_payload.json": partner_review_payload,
        "partner_agent_requests.json": partner_agent_requests,
    }

    for filename, data in outputs.items():
        _write_json(output_dir / filename, data)

    print(f"Exported backend demo bundle to: {output_dir}")
    print("")
    print("Generated files:")
    for filename in outputs:
        print(f"- {filename}")

    print("")
    print("Summary:")
    print(f"- backend_status: {backend_status.get('overall_status')}")
    print(f"- frontend_decision: {frontend_payload.get('decision')}")
    print(f"- backend_contract_valid: {frontend_payload.get('backend_validation', {}).get('response_contract_valid')}")
    print(f"- agents_called: {', '.join(frontend_payload.get('agents_called', []))}")
    print(f"- partner_payload_items: {len(partner_review_payload.get('selected_items', []))}")
    print(f"- partner_requests_ready: {partner_agent_requests.get('is_ready_for_partner_calls')}")




def _export_compact_frontend_payload_after_bundle() -> None:
    output_dir = Path("demo_outputs")
    frontend_payload_path = output_dir / "frontend_payload_shopping.json"
    compact_payload_path = output_dir / "frontend_payload_compact.json"

    if not frontend_payload_path.exists():
        print("Compact frontend payload skipped: frontend_payload_shopping.json was not found.")
        return

    full_payload = json.loads(frontend_payload_path.read_text(encoding="utf-8"))
    compact_payload = build_compact_frontend_payload(full_payload)

    compact_payload_path.write_text(
        json.dumps(compact_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("- frontend_payload_compact.json")


_original_main_for_compact_export = main


def main() -> None:
    _original_main_for_compact_export()
    _export_compact_frontend_payload_after_bundle()


if __name__ == "__main__":
    main()
