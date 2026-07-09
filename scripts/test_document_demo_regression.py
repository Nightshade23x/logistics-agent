from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DOCUMENT_OUTPUTS = [
    (
        "single document agent",
        [sys.executable, "scripts/run_document_agent.py"],
        [
            "DOCUMENT AI REPORT",
            "Document type: packing_list",
            "Validation status: ready_for_review",
            "EXTRACTED ITEMS",
            "Target agent: logistics_agent",
            "Target agent: compliance_agent",
            "Target agent: finance_agent",
        ],
    ),
    (
        "document pair agent",
        [sys.executable, "scripts/run_document_pair_agent.py"],
        [
            "DOCUMENT PAIR VALIDATION REPORT",
            "Validation status: ready_for_review",
            "Mismatch count: 0",
            "No invoice vs packing list mismatches detected.",
            "Target agent: logistics_agent",
            "Target agent: finance_agent",
            "Target agent: compliance_agent",
        ],
    ),
    (
        "document set agent",
        [sys.executable, "scripts/run_document_set_agent.py"],
        [
            "DOCUMENT SET COMPLETENESS REPORT",
            "Validation status: ready_for_review",
            "Present: bill_of_lading, certificate_of_origin, invoice, packing_list",
            "Missing: none",
            "Target agent: logistics_agent",
            "Target agent: finance_agent",
            "Target agent: compliance_agent",
        ],
    ),
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
    unit_tests = [
        "scripts/test_document_agent.py",
        "scripts/test_document_quality_review.py",
        "scripts/test_document_requirements_advisor.py",
        "scripts/test_trade_compliance_readiness_advisor.py",
    ]

    for test_script in unit_tests:
        output = run_command([sys.executable, test_script])
        print(output.strip())

    for name, command, expected_lines in EXPECTED_DOCUMENT_OUTPUTS:
        output = run_command(command)

        for expected_line in expected_lines:
            assert_contains(output, expected_line, name)

        print(f"PASS: {name}")

    print("PASS: document demo regression checks passed")


if __name__ == "__main__":
    main()
