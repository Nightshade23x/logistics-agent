from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "demo_outputs" / "frontend_demo.html"

RAW_ENUMS_THAT_SHOULD_NOT_RENDER = [
    "review_required",
    "needs_more_information",
    "fill_missing_information",
    "fcl_preferred",
    "ready_for_review_with_high_risk",
    "partner_review_not_configured",
    "non_stackable",
    "front_floor_base_zone",
    "protected_middle_zone",
]


def main() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/export_static_frontend_demo.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    output = result.stdout + "\n" + result.stderr

    if result.returncode != 0:
        print(output)
        raise SystemExit(result.returncode)

    assert HTML_PATH.exists(), f"Missing exported HTML: {HTML_PATH}"

    html = HTML_PATH.read_text(encoding="utf-8")

    for raw_enum in RAW_ENUMS_THAT_SHOULD_NOT_RENDER:
        if raw_enum in html:
            print(f"FAILED: raw enum still visible in static frontend HTML: {raw_enum}")
            raise SystemExit(1)

    expected_labels = [
        "Review Required",
        "Needs More Information",
        "Fill Missing Information",
        "FCL Preferred",
        "Ready For Review With High Risk",
        "Partner Review Not Configured",
        "Non Stackable",
    ]

    for label in expected_labels:
        assert label in html, f"Missing expected display label: {label}"

    print("PASS: static frontend demo uses human-readable display labels")


if __name__ == "__main__":
    main()
