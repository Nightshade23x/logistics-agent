from __future__ import annotations

import os
import py_compile
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PARTNER_AGENT_FOLDERS = [
    ROOT / "finance_agent",
    ROOT / "compliance_agent",
    ROOT / "risk_agent",
    ROOT / "orchestrator_agent",
]

TEST_TARGETS = [
    "finance_agent/tests",
    "compliance_agent/compliance_agent/tests",
    "risk_agent/risk_agent/tests",
    "orchestrator_agent/tests",
]


def run_step(name: str, command: list[str], env: dict[str, str] | None = None) -> None:
    print()
    print("=" * 88)
    print(f"RUNNING: {name}")
    print("=" * 88)

    completed = subprocess.run(command, cwd=ROOT, env=env)

    if completed.returncode != 0:
        raise SystemExit(f"FAILED: {name}")

    print()
    print(f"PASSED: {name}")


def compile_partner_agents() -> None:
    print()
    print("=" * 88)
    print("RUNNING: Compile partner agent Python files")
    print("=" * 88)

    failed: list[str] = []

    for folder in PARTNER_AGENT_FOLDERS:
        if not folder.exists():
            failed.append(str(folder.relative_to(ROOT)))
            print(f"MISSING FOLDER: {folder.relative_to(ROOT)}")
            continue

        for path in folder.rglob("*.py"):
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                failed.append(str(path.relative_to(ROOT)))
                print(f"FAILED: {path.relative_to(ROOT)}")
                print(exc)

    if failed:
        raise SystemExit(f"Compile failed for {len(failed)} partner-agent file(s).")

    print()
    print("PASSED: Compile partner agent Python files")


def main() -> None:
    env = os.environ.copy()

    pythonpath_parts = [
        str(ROOT),
        str(ROOT / "trader_agent"),
        str(ROOT / "finance_agent"),
        str(ROOT / "compliance_agent"),
        str(ROOT / "risk_agent"),
        str(ROOT / "orchestrator_agent"),
    ]

    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)

    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    compile_partner_agents()

    for target in TEST_TARGETS:
        run_step(
            name=f"pytest {target}",
            command=[sys.executable, "-m", "pytest", target, "-q"],
            env=env,
        )

    print()
    print("=" * 88)
    print("PARTNER AGENT SMOKE SUITE SUMMARY")
    print("=" * 88)
    print("ALL PARTNER AGENT SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
