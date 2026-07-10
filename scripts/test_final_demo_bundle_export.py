from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "demo_outputs" / "final_demo_bundle"

EXPECTED_FILES = [
    "README.md",
    "checks/all_demo_checks.txt",
    "checks/export_demo_pack_output.txt",
    "checks/static_frontend_demo_output.txt",
    "shopping_demo/frontend_payload_compact.json",
    "shopping_demo/frontend_payload_shopping.json",
    "shopping_demo/backend_status.json",
    "frontend/frontend_demo.html",
    "logistics/logistics_scenario_pack.txt",
    "logistics/oversized_logistics_report.txt",
    "documents/document_agent_report.txt",
    "documents/document_pair_validation_report.txt",
    "documents/document_set_completeness_report.txt",
    "partner/live_partner_stack_check.txt",
    "docs/demo_runbook.md",
    "docs/frontend_payload_contract.md",
    "docs/backend_agent_status_report.md",
]


def main() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/export_final_demo_bundle.py"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    output = result.stdout + "\n" + result.stderr

    if result.returncode != 0:
        print(output)
        raise SystemExit(result.returncode)

    for relative_path in EXPECTED_FILES:
        path = BUNDLE / relative_path
        assert path.exists(), f"Missing expected bundle file: {relative_path}"
        assert path.stat().st_size > 0, f"Empty bundle file: {relative_path}"

    frontend_html = (BUNDLE / "frontend" / "frontend_demo.html").read_text(encoding="utf-8")

    assert "Logistics Agent Frontend Demo" in frontend_html
    assert "Review Required" in frontend_html
    assert "Logistics Visualizer" in frontend_html
    assert "frontend_demo.html" in (BUNDLE / "README.md").read_text(encoding="utf-8")

    print("PASS: final demo bundle includes backend, logistics, document, partner, docs, and static frontend outputs")


if __name__ == "__main__":
    main()
