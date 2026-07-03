from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.item_resolver import resolve_items
from app.logistics_agent import build_logistics_plan
from app.report_formatter import format_logistics_plan


def _get_shipment_path() -> Path:
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])

        if input_path.is_absolute():
            return input_path

        return ROOT_DIR / input_path

    return ROOT_DIR / "data" / "sample_shipment.json"


def main() -> None:
    shipment_path = _get_shipment_path()

    with shipment_path.open("r", encoding="utf-8-sig") as file:
        shipment_data = json.load(file)

    resolution = resolve_items(shipment_data["items"])

    shipment_context = {
        "shipment_id": shipment_data.get("shipment_id"),
        "customer": shipment_data.get("customer"),
        "origin": shipment_data.get("origin"),
        "destination": shipment_data.get("destination"),
        "notes": shipment_data.get("notes"),
    }

    plan = build_logistics_plan(
        resolution["resolved_items"],
        shipment_context=shipment_context,
    )

    plan["input_resolution"] = {
        "issues": resolution["issues"],
        "unresolved_items": resolution["unresolved_items"],
    }

    shipment_info = {
        "shipment_id": shipment_data.get("shipment_id"),
        "customer": shipment_data.get("customer"),
        "origin": shipment_data.get("origin"),
        "destination": shipment_data.get("destination"),
        "notes": shipment_data.get("notes"),
    }

    report = format_logistics_plan(plan, shipment_info)
    print(report)


if __name__ == "__main__":
    main()
