from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import (
    process_document_files_request,
    process_json_file_request,
    process_text_request,
)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, default=str))


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage:")
        print('python scripts\\run_frontend_payload.py text "I need 50 TVs..."')
        print("python scripts\\run_frontend_payload.py json data\\suppliers\\sample_shopping_request.json")
        print("python scripts\\run_frontend_payload.py files data\\documents\\sample_invoice.txt data\\documents\\sample_packing_list.txt")
        print("")
        print("Optional:")
        print("--raw    Include full raw backend response for debugging")
        raise SystemExit(1)

    mode = sys.argv[1].lower()
    include_raw_response = "--raw" in sys.argv
    args = [arg for arg in sys.argv[2:] if arg != "--raw"]

    if mode == "text":
        user_text = " ".join(args)
        payload = process_text_request(
            user_text,
            include_raw_response=include_raw_response,
        )

    elif mode == "json":
        payload = process_json_file_request(
            Path(args[0]),
            include_raw_response=include_raw_response,
        )

    elif mode == "files":
        payload = process_document_files_request(
            [Path(path) for path in args],
            include_raw_response=include_raw_response,
        )

    else:
        raise SystemExit(f"Unknown mode: {mode}")

    _print_json(payload)


if __name__ == "__main__":
    main()
