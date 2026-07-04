from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.document_set_service import run_document_set_agent_from_files


def main() -> None:
    if len(sys.argv) > 1:
        paths = [Path(arg) for arg in sys.argv[1:]]
    else:
        paths = [
            ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
            ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
            ROOT_DIR / "data" / "documents" / "sample_bill_of_lading.txt",
            ROOT_DIR / "data" / "documents" / "sample_certificate_of_origin.txt",
        ]

    response = run_document_set_agent_from_files(paths)

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
