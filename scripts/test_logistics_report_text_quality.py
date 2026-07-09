from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BAD_PATTERNS = [
    "and800",
    "thecontainer",
    "aboveit",
    "unnecessarytransfers",
    "loadingequipment",
    "weights,and",
    "directcontact",
    "handlingrequirements",
    "pressureand",
    "haveitems",
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


def check_text_quality(name: str, text: str) -> None:
    failures = []

    for pattern in BAD_PATTERNS:
        if pattern in text:
            failures.append(pattern)

    if failures:
        print(f"FAILED: {name}")
        print("Found joined-word patterns:")
        for pattern in failures:
            print(f"- {pattern}")
        raise SystemExit(1)

    print(f"PASS: {name}")


def main() -> None:
    scenario_pack_output = run_command(
        [sys.executable, "scripts/run_logistics_scenarios.py"]
    )

    oversized_report_output = run_command(
        [
            sys.executable,
            "scripts/run_logistics_plan.py",
            "data/scenarios/oversized_multi_container.json",
        ]
    )

    check_text_quality("logistics scenario pack text quality", scenario_pack_output)
    check_text_quality("oversized logistics report text quality", oversized_report_output)

    print("PASS: logistics report text quality checks passed")


if __name__ == "__main__":
    main()
