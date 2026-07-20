from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_HTML = ROOT / "demo_outputs" / "frontend_demo.html"

BRAVE_CANDIDATES = [
    Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
]


def run_export() -> None:
    env = os.environ.copy()
    env.pop("TRADE_ORCHESTRATOR_BASE_URL", None)
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, "scripts/export_static_frontend_demo.py"],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    if result.stdout.strip():
        print(result.stdout)

    if result.stderr.strip():
        print(result.stderr)

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def find_brave() -> Path | None:
    for candidate in BRAVE_CANDIDATES:
        if candidate.exists():
            return candidate

    return None


def open_frontend() -> None:
    if not FRONTEND_HTML.exists():
        raise SystemExit(f"Missing frontend HTML: {FRONTEND_HTML}")

    brave_path = find_brave()

    if brave_path:
        subprocess.Popen([str(brave_path), str(FRONTEND_HTML)])
        print(f"Opened static frontend demo in Brave: {FRONTEND_HTML}")
        return

    try:
        os.startfile(FRONTEND_HTML)  # type: ignore[attr-defined]
        print(f"Opened static frontend demo with default browser: {FRONTEND_HTML}")
        return
    except Exception as exc:
        print("Could not open browser automatically.")
        print(f"Reason: {exc}")
        print("")
        print("Open this file manually:")
        print(FRONTEND_HTML)
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export and optionally open the static frontend demo.")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Generate the frontend HTML but do not open a browser.",
    )

    args = parser.parse_args()

    run_export()

    if not FRONTEND_HTML.exists():
        raise SystemExit(f"Export did not create expected file: {FRONTEND_HTML}")

    print(f"Static frontend demo ready: {FRONTEND_HTML}")

    if not args.no_open:
        open_frontend()


if __name__ == "__main__":
    main()
