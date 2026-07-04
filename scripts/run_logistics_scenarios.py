from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.logistics_service import run_logistics_agent


SCENARIO_DIR = ROOT_DIR / "data" / "scenarios"


def load_scenario(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def main() -> None:
    scenario_files = sorted(SCENARIO_DIR.glob("*.json"))

    if not scenario_files:
        print("No scenario files found.")
        return

    print("LOGISTICS AGENT SCENARIO PACK")
    print("=" * 40)

    for scenario_path in scenario_files:
        shipment_data = load_scenario(scenario_path)
        response = run_logistics_agent(shipment_data)

        print("")
        print(f"Scenario file: {scenario_path.name}")
        print("-" * 40)
        print(f"Shipment ID: {shipment_data.get('shipment_id')}")
        print(f"Status: {response['status']}")
        print(f"Summary: {response['summary']}")

        missing_info = response.get("missing_information", [])
        if missing_info:
            print("Missing information:")
            for item in missing_info[:5]:
                print(f"- {item}")

        handoff_requests = response.get("handoff_requests", [])
        if handoff_requests:
            print("Handoff requests:")
            for request in handoff_requests:
                print(f"- {request['target_agent']}: {request['reason']}")


if __name__ == "__main__":
    main()
