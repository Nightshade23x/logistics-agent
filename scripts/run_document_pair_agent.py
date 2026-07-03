from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.document_pair_service import run_document_pair_agent_from_files


def main() -> None:
    if len(sys.argv) >= 3:
        invoice_path = Path(sys.argv[1])
        packing_list_path = Path(sys.argv[2])
    else:
        invoice_path = ROOT_DIR / "data" / "documents" / "sample_invoice.txt"
        packing_list_path = ROOT_DIR / "data" / "documents" / "sample_packing_list.txt"

    response = run_document_pair_agent_from_files(invoice_path, packing_list_path)

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
