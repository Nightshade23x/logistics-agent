from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TRACKED_PATH_PARTS = [
    "__pycache__",
    ".venv",
    "demo_outputs/",
    "local_secrets.ps1",
    "start_orchestrator_local.ps1",
]

FORBIDDEN_TRACKED_SUFFIXES = [
    ".pyc",
    ".pyo",
    ".env",
    ".env.local",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
]


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(result.returncode)

    return result.stdout


def main() -> None:
    tracked_files = [
        line.strip().replace("\\", "/")
        for line in run_git(["ls-files"]).splitlines()
        if line.strip()
    ]

    failures: list[str] = []

    for tracked_file in tracked_files:
        lowered = tracked_file.lower()

        is_allowed_env_template = lowered.endswith(".example.env") or lowered.endswith(".sample.env")

        for forbidden_part in FORBIDDEN_TRACKED_PATH_PARTS:
            if forbidden_part.lower() in lowered:
                failures.append(f"Forbidden tracked path: {tracked_file}")

        for suffix in FORBIDDEN_TRACKED_SUFFIXES:
            if lowered.endswith(suffix.lower()) and not is_allowed_env_template:
                failures.append(f"Forbidden tracked file suffix: {tracked_file}")

    for tracked_file in tracked_files:
        path = ROOT / tracked_file

        if not path.exists() or path.is_dir():
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"Possible secret detected in tracked file: {tracked_file}")

    if failures:
        print("FAILED: repo hygiene check found issues")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("PASS: repo hygiene check found no tracked secrets or generated files")


if __name__ == "__main__":
    main()
