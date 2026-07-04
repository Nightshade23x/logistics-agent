from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.shopping_service import run_shopping_agent_from_any_file


def main() -> None:
    if len(sys.argv) > 1:
        request_path = Path(sys.argv[1])
    else:
        request_path = ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"

    response = run_shopping_agent_from_any_file(request_path)

    print(response["report"])
    print("")
    print("AGENT STATUS")
    print("-" * 30)
    print(response["status"])
    print("")
    print("AGENT SUMMARY")
    print("-" * 30)
    print(response["summary"])
    print("")
    print("INPUT RESOLUTION")
    print("-" * 30)
    print(f"Source: {response['input_resolution']['source']}")
    print(f"Input type: {response['input_resolution'].get('input_type')}")
    print("")
    print("HANDOFF REQUESTS")
    print("-" * 30)

    for request in response["handoff_requests"]:
        print(f"Target agent: {request['target_agent']}")
        print(f"Reason: {request['reason']}")
        print("Inputs needed:")
        for item in request["inputs_needed"]:
            print(f"- {item}")
        print("")


if __name__ == "__main__":
    main()
