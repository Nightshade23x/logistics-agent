from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.compact_frontend_payload import build_compact_frontend_payload
from app.demo_report_builder import build_demo_report


def main() -> None:
    output_dir = ROOT_DIR / "demo_outputs"
    output_dir.mkdir(exist_ok=True)

    full_payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )
    compact_payload = build_compact_frontend_payload(full_payload)

    report = build_demo_report(compact_payload)

    output_path = output_dir / "demo_report.md"
    output_path.write_text(report, encoding="utf-8")

    print(f"Exported demo report to: {output_path}")


if __name__ == "__main__":
    main()
