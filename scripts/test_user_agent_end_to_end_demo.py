from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_OUTPUT_LINES = [
    "DEMO 1: Shopping JSON -> Shopping Agent -> Logistics Agent -> Partner Review",
    "DEMO 2: Documents -> Document AI Agent -> Logistics Agent -> Partner Review",
    "DEMO 3: Plain English request -> Shopping Agent -> Logistics Agent",
    "Detected intent: shopping",
    "Detected intent: document",
    "shopping_agent",
    "document_ai_agent",
    "logistics_agent",
    "partner_review_service",
    "Logistics metrics:",
    "Partner review:",
    "Final verdict:",
    "Missing information count:",
    "Recommended container: 20ft Standard Container",
]


def main() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/demo_user_agent_summary.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    output = result.stdout + "\n" + result.stderr

    if result.returncode != 0:
        print(output)
        raise SystemExit(result.returncode)

    for expected_line in EXPECTED_OUTPUT_LINES:
        if expected_line not in output:
            print("FAILED: missing expected output line")
            print(f"Expected: {expected_line}")
            print("\nOutput preview:")
            print(output[:5000])
            raise SystemExit(1)

    demo_count = output.count("DEMO ")
    assert demo_count >= 3, f"Expected at least 3 demo flows, found {demo_count}"

    assert "DEMO 1" in output and "partner_review_not_configured" in output
    assert "DEMO 2" in output and "document_ai_agent" in output
    assert "DEMO 3" in output and "Plain English request" in output

    print("PASS: end-to-end user agent demo flows work")


if __name__ == "__main__":
    main()
