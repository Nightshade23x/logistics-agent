from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app" / "streamlit_frontend.py"

BRAVE_CANDIDATES = [
    Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
]


def find_brave() -> Path | None:
    for candidate in BRAVE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def open_browser(url: str) -> None:
    brave = find_brave()

    if brave:
        subprocess.Popen([str(brave), url])
        print(f"Opened Streamlit frontend in Brave: {url}")
        return

    try:
        os.startfile(url)  # type: ignore[attr-defined]
        print(f"Opened Streamlit frontend in default browser: {url}")
    except Exception as exc:
        print("Could not open browser automatically.")
        print(f"Reason: {exc}")
        print(f"Open manually: {url}")


def build_command(port: int, open_browser_tab: bool) -> list[str]:
    # Always run Streamlit in headless mode so Streamlit itself does not open
    # a browser tab. This launcher opens Brave manually exactly once.
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_PATH),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the Streamlit frontend demo.")
    parser.add_argument("--port", type=int, default=8505)
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Start Streamlit but do not open the browser.",
    )
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="Print the Streamlit command and exit.",
    )

    args = parser.parse_args()

    if not APP_PATH.exists():
        raise SystemExit(f"Missing Streamlit app: {APP_PATH}")

    url = f"http://localhost:{args.port}"
    command = build_command(port=args.port, open_browser_tab=not args.no_open)

    if args.print_command:
        print(" ".join(command))
        return

    print("Starting Streamlit frontend demo...")
    print(f"URL: {url}")
    print("Press Ctrl + C to stop the server.")
    print("")

    process = subprocess.Popen(command, cwd=ROOT)

    try:
        if not args.no_open:
            time.sleep(3)
            open_browser(url)

        process.wait()

    except KeyboardInterrupt:
        print("")
        print("Stopping Streamlit frontend...")
        process.terminate()

        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()

        print("Streamlit frontend stopped.")


if __name__ == "__main__":
    main()
