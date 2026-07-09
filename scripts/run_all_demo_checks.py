from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CHECKS = [
    (
        "Compile key backend modules",
        [
            sys.executable,
            "-m",
            "py_compile",
            "app/frontend_payload.py",
            "app/compact_frontend_payload.py",
            "app/partner_adapters/trade_orchestrator_client.py",
        ],
    ),
    (
        "Trade orchestrator adapter tests",
        [sys.executable, "scripts/test_trade_orchestrator_client.py"],
    ),
    (
        "Frontend payload tests",
        [sys.executable, "scripts/test_frontend_payload.py"],
    ),
    (
        "Compact frontend payload tests",
        [sys.executable, "scripts/test_compact_frontend_payload.py"],
    ),
    (
        "Logistics visualizer payload test",
        [sys.executable, "scripts/test_logistics_visualizer_payload.py"],
    ),
    (
        "Payload text quality test",
        [sys.executable, "scripts/test_payload_text_quality.py"],
    ),
    (
        "Logistics report text quality test",
        [sys.executable, "scripts/test_logistics_report_text_quality.py"],
    ),
    (
        "Standalone demo check",
        [sys.executable, "scripts/run_demo_standalone_check.py"],
    ),
]


def run_check(name: str, command: list[str]) -> None:
    print(f"\n=== {name} ===")
    print(" ".join(command))

    env = os.environ.copy()
    env.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    if result.stdout.strip():
        print(result.stdout)

    if result.stderr.strip():
        print(result.stderr)

    if result.returncode != 0:
        print(f"FAILED: {name}")
        raise SystemExit(result.returncode)

    print(f"PASSED: {name}")


def main() -> None:
    print("Running all standalone demo checks...")
    print("Live partner services are not required for this script.")

    for name, command in CHECKS:
        run_check(name, command)

    print("\nALL DEMO CHECKS PASSED")
    print("Standalone backend, frontend payload, visualizer, text quality, and adapter checks are OK.")


if __name__ == "__main__":
    main()
