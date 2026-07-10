from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_HTML = ROOT / "demo_outputs" / "frontend_demo.html"


def main() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/open_static_frontend_demo.py", "--no-open"],
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

    assert FRONTEND_HTML.exists(), f"Missing frontend HTML: {FRONTEND_HTML}"

    html = FRONTEND_HTML.read_text(encoding="utf-8")

    assert "Logistics Agent Frontend Demo" in html
    assert "Logistics Visualizer" in html
    assert "Review Required" in html

    print("PASS: static frontend launcher exports demo HTML without opening browser")


if __name__ == "__main__":
    main()
