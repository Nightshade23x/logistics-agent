from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SCENARIO_STATUS_LINES = [
    ("hazardous_cargo.json", "Status: critical_review_required"),
    ("normal_dry_cargo.json", "Status: ready_for_review"),
    ("oversized_multi_container.json", "Status: critical_review_required"),
    ("perishable_cargo.json", "Status: review_required"),
    ("unknown_item_missing_dimensions.json", "Status: partial_plan_needs_more_information"),
]

EXPECTED_OVERSIZED_REPORT_LINES = [
    "Shipment ID: SCENARIO-OVERSIZED-001",
    "Recommended container: Multiple containers or specialist planning required",
    "Fit status: FITS_SELECTED_CONTAINER",
    "Risk level: CRITICAL",
    "CONTAINER OPTIONS",
    "CONTAINER LAYOUT DRAFT",
    "SUGGESTED LOADING SEQUENCE",
    "SHIPMENT READINESS CHECKLIST",
    "Container plan is not final because the shipment exceeds standard safe planning limits.",
]


def run_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    output = result.stdout + "\n" + result.stderr

    if result.returncode != 0:
        print(output)
        raise SystemExit(result.returncode)

    return output


def assert_contains(output: str, expected: str, context: str) -> None:
    if expected not in output:
        print(f"FAILED: missing expected text in {context}")
        print(f"Expected: {expected}")
        print("\nOutput preview:")
        print(output[:3000])
        raise SystemExit(1)


def main() -> None:
    scenario_output = run_command(
        [sys.executable, "scripts/run_logistics_scenarios.py"]
    )

    for filename, expected_status_line in EXPECTED_SCENARIO_STATUS_LINES:
        assert_contains(scenario_output, f"Scenario file: {filename}", "scenario pack")
        assert_contains(scenario_output, expected_status_line, filename)
        print(f"PASS: {filename} -> {expected_status_line}")

    oversized_output = run_command(
        [
            sys.executable,
            "scripts/run_logistics_plan.py",
            "data/scenarios/oversized_multi_container.json",
        ]
    )

    for expected_line in EXPECTED_OVERSIZED_REPORT_LINES:
        assert_contains(oversized_output, expected_line, "oversized logistics report")

    print("PASS: oversized logistics report contains expected planning sections")
    print("PASS: logistics scenario regression checks passed")


if __name__ == "__main__":
    main()
