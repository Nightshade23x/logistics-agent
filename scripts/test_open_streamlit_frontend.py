from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/open_streamlit_frontend.py",
            "--port",
            "8505",
            "--no-open",
            "--print-command",
        ],
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

    assert "streamlit" in output
    assert "app\\streamlit_frontend.py" in output or "app/streamlit_frontend.py" in output
    assert "--server.port 8505" in output

    print("PASS: Streamlit frontend launcher command is valid")


if __name__ == "__main__":
    main()
