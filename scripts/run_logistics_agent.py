from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.logistics_service import run_logistics_agent


def _get_shipment_path() -> Path:
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])

        if input_path.is_absolute():
            return input_path

        return ROOT_DIR / input_path

    return ROOT_DIR / "data" / "simple_shipment.json"


def main() -> None:
    shipment_path = _get_shipment_path()

    with shipment_path.open("r", encoding="utf-8-sig") as file:
        shipment_data = json.load(file)

    response = run_logistics_agent(shipment_data)

    print(response["report"])
    print("")
    print("AGENT STATUS")
    print("-" * 30)
    print(response["status"])
    print("")
    print("AGENT SUMMARY")
    print("-" * 30)
    print(response["summary"])

    handoff_requests = response.get("handoff_requests", [])
    if handoff_requests:
        print("")
        print("HANDOFF REQUESTS")
        print("-" * 30)

        for request in handoff_requests:
            print(f"Target agent: {request['target_agent']}")
            print(f"Reason: {request['reason']}")
            print("Inputs needed:")
            for item in request["inputs_needed"]:
                print(f"- {item}")
            print("")


if __name__ == "__main__":
    main()
