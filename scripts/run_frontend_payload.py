from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.frontend_payload import build_frontend_payload
from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json_file,
    run_user_agent_from_text,
)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, default=str))


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage:")
        print('python scripts\\run_frontend_payload.py text "I need 50 TVs..."')
        print("python scripts\\run_frontend_payload.py json data\\suppliers\\sample_shopping_request.json")
        print("python scripts\\run_frontend_payload.py files data\\documents\\sample_invoice.txt data\\documents\\sample_packing_list.txt")
        raise SystemExit(1)

    include_raw_response = "--raw" in sys.argv
    args = [arg for arg in sys.argv[2:] if arg != "--raw"]

    mode = sys.argv[1].lower()

    if mode == "text":
        user_text = " ".join(args)
        response = run_user_agent_from_text(user_text)

    elif mode == "json":
        response = run_user_agent_from_json_file(Path(args[0]))

    elif mode == "files":
        paths = [Path(path) for path in args]
        response = run_user_agent_from_files(paths)

    else:
        raise SystemExit(f"Unknown mode: {mode}")

    payload = build_frontend_payload(response, include_raw_response=include_raw_response)
    _print_json(payload)


if __name__ == "__main__":
    main()
