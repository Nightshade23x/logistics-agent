from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.backend_status import build_backend_status
from app.compact_frontend_payload import build_compact_frontend_payload
from app.demo_report_builder import build_demo_report


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _build_demo_index(
    backend_status: dict,
    full_payload: dict,
    compact_payload: dict,
) -> str:
    executive_summary = compact_payload.get("executive_summary", {})
    booking_readiness = compact_payload.get("booking_readiness", {})
    logistics_metrics = compact_payload.get("logistics_metrics", {})

    lines = [
        "# Demo Pack Index",
        "",
        "## What this demo shows",
        "",
        "- User Agent routes a shopping request.",
        "- Shopping Agent selects suppliers and procurement options.",
        "- Logistics Agent plans cargo volume, weight, container, and risk.",
        "- Partner Review prepares Risk, Compliance, Trader, and Finance checks.",
        "- Backend produces executive summary, UI sections, booking readiness, and action plan.",
        "",
        "## System Status",
        "",
        f"- **overall_status**: {backend_status.get('overall_status')}",
        f"- **local_demo_ready**: {backend_status.get('local_demo_ready')}",
        f"- **live_partner_ready**: {backend_status.get('live_partner_ready')}",
        "",
        "## Executive Summary",
        "",
        f"- **headline**: {executive_summary.get('headline')}",
        f"- **decision**: {compact_payload.get('decision')}",
        f"- **ready_for_first_pass**: {executive_summary.get('ready_for_first_pass')}",
        f"- **ready_for_booking**: {executive_summary.get('ready_for_booking')}",
        f"- **booking_score**: {executive_summary.get('booking_score')}",
        f"- **next_gate**: {executive_summary.get('next_gate')}",
        "",
        "## Shipment Snapshot",
        "",
        f"- **estimated_procurement_cost_usd**: {executive_summary.get('shipment_snapshot', {}).get('estimated_procurement_cost_usd')}",
        f"- **total_cbm**: {logistics_metrics.get('total_cbm')}",
        f"- **total_weight_kg**: {logistics_metrics.get('total_weight_kg')}",
        f"- **recommended_container**: {logistics_metrics.get('recommended_container')}",
        f"- **risk_level**: {logistics_metrics.get('risk_level')}",
        f"- **partner_review_status**: {compact_payload.get('partner_review_status')}",
        "",
        "## Generated Files",
        "",
        "- `backend_status.json` — local readiness and missing partner connections.",
        "- `frontend_payload_shopping.json` — full backend/frontend payload.",
        "- `frontend_payload_compact.json` — compact frontend-ready payload.",
        "- `demo_report.md` — readable mentor/demo report.",
        "- `demo_index.md` — this index.",
        "",
        "## Recommended Demo Command",
        "",
        "```powershell",
        "python scripts\\export_demo_pack.py",
        "```",
        "",
        "## Booking Readiness",
        "",
        f"- **status**: {booking_readiness.get('status')}",
        f"- **ready_for_first_pass**: {booking_readiness.get('ready_for_first_pass')}",
        f"- **ready_for_booking**: {booking_readiness.get('ready_for_booking')}",
        f"- **next_gate**: {booking_readiness.get('next_gate')}",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    output_dir = ROOT_DIR / "demo_outputs"
    output_dir.mkdir(exist_ok=True)

    sample_path = ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"

    backend_status = build_backend_status()
    full_payload = process_json_file_request(sample_path)
    compact_payload = build_compact_frontend_payload(full_payload)
    demo_report = build_demo_report(compact_payload)
    demo_index = _build_demo_index(
        backend_status=backend_status,
        full_payload=full_payload,
        compact_payload=compact_payload,
    )

    _write_json(output_dir / "backend_status.json", backend_status)
    _write_json(output_dir / "frontend_payload_shopping.json", full_payload)
    _write_json(output_dir / "frontend_payload_compact.json", compact_payload)

    (output_dir / "demo_report.md").write_text(demo_report, encoding="utf-8")
    (output_dir / "demo_index.md").write_text(demo_index, encoding="utf-8")

    print(f"Exported demo pack to: {output_dir}")
    print("")
    print("Generated files:")
    print("- backend_status.json")
    print("- frontend_payload_shopping.json")
    print("- frontend_payload_compact.json")
    print("- demo_report.md")
    print("- demo_index.md")
    print("")
    print("Summary:")
    print(f"- overall_status: {backend_status.get('overall_status')}")
    print(f"- decision: {compact_payload.get('decision')}")
    print(f"- ready_for_first_pass: {compact_payload.get('executive_summary', {}).get('ready_for_first_pass')}")
    print(f"- ready_for_booking: {compact_payload.get('executive_summary', {}).get('ready_for_booking')}")
    print(f"- partner_review_status: {compact_payload.get('partner_review_status')}")


if __name__ == "__main__":
    main()
