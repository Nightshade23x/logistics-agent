from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.shopping_service import run_shopping_agent_from_any_file
from app.supplier_shortlist import (
    export_supplier_shortlist_csv,
    export_supplier_shortlist_json,
)


def main() -> None:
    if len(sys.argv) > 1:
        request_path = Path(sys.argv[1])
    else:
        request_path = ROOT_DIR / "data" / "suppliers" / "sample_shopping_request_text.txt"

    response = run_shopping_agent_from_any_file(request_path)
    shortlist = response["handoff_payload"]["supplier_shortlist"]

    output_dir = ROOT_DIR / "outputs"
    json_path = output_dir / "supplier_shortlist.json"
    csv_path = output_dir / "supplier_shortlist.csv"

    export_supplier_shortlist_json(shortlist, json_path)
    export_supplier_shortlist_csv(shortlist, csv_path)

    print("Supplier shortlist exported.")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    print(f"Rows: {len(shortlist)}")


if __name__ == "__main__":
    main()
