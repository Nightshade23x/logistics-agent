from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_export_demo_pack_creates_expected_files():
    result = subprocess.run(
        [sys.executable, "scripts/export_demo_pack.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    output_dir = ROOT_DIR / "demo_outputs"

    expected_files = [
        "backend_status.json",
        "frontend_payload_shopping.json",
        "frontend_payload_compact.json",
        "demo_report.md",
        "demo_index.md",
    ]

    for filename in expected_files:
        assert (output_dir / filename).exists(), f"Missing {filename}"

    index_text = (output_dir / "demo_index.md").read_text(encoding="utf-8")

    assert "# Demo Pack Index" in index_text
    assert "ready_for_first_pass" in index_text
    assert "frontend_payload_compact.json" in index_text


def main() -> None:
    test_export_demo_pack_creates_expected_files()

    print("All demo pack exporter tests passed.")


if __name__ == "__main__":
    main()
