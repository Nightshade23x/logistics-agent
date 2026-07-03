from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.logistics_service import run_logistics_agent
from app.text_shipment_parser import parse_shipment_text


def _get_text_input() -> str:
    if len(sys.argv) > 1:
        input_value = " ".join(sys.argv[1:])
        possible_path = ROOT_DIR / input_value

        if possible_path.exists():
            return possible_path.read_text(encoding="utf-8-sig")

        return input_value

    return (ROOT_DIR / "data" / "text_request_demo.txt").read_text(encoding="utf-8-sig")


def main() -> None:
    text = _get_text_input()
    parsed = parse_shipment_text(text)

    shipment_data = {
        "shipment_id": "TEXT-DEMO-001",
        "customer": "Text Input Demo",
        "origin": "India",
        "destination": "USA",
        "notes": "Generated from simple text input.",
        "items": parsed["items"],
    }

    response = run_logistics_agent(shipment_data)

    print("TEXT PARSING RESULT")
    print("-" * 30)
    print(f"Original text: {text.strip()}")
    print(f"Parsed items: {len(parsed['items'])}")

    if parsed["issues"]:
        print("Parsing issues:")
        for issue in parsed["issues"]:
            print(f"- {issue}")

    print("")
    print(response["report"])
    print("")
    print("AGENT STATUS")
    print("-" * 30)
    print(response["status"])


if __name__ == "__main__":
    main()
