from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.compact_frontend_payload import build_compact_frontend_payload
from app.demo_report_builder import build_demo_report


def test_demo_report_from_compact_payload():
    full_payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )
    compact_payload = build_compact_frontend_payload(full_payload)

    report = build_demo_report(compact_payload)

    assert "# Logistics Agent Demo Report" in report
    assert "## Executive Decision" in report
    assert "## Shipment Snapshot" in report
    assert "## Top Risks" in report
    assert "## Next Actions" in report
    assert "20ft Standard Container" in report
    assert "partner_review_not_configured" in report


def test_demo_report_from_full_payload():
    full_payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    report = build_demo_report(full_payload)

    assert "# Logistics Agent Demo Report" in report
    assert "ready_for_first_pass" in report
    assert "India" in report
    assert "USA" in report


def main() -> None:
    test_demo_report_from_compact_payload()
    test_demo_report_from_full_payload()

    print("All demo report builder tests passed.")


if __name__ == "__main__":
    main()
