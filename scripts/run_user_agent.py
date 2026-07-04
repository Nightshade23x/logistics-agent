from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json_file,
    run_user_agent_from_text,
)


def _print_response(response: dict) -> None:
    print("USER AGENT RESPONSE")
    print("=" * 30)
    print(f"Status: {response['status']}")
    print(f"Detected intent: {response['detected_intent']}")
    print(f"Agents called: {response['agents_called']}")
    print(f"Summary: {response['summary']}")
    print("")

    if response["missing_information"]:
        print("MISSING INFORMATION")
        print("-" * 30)
        for item in response["missing_information"]:
            print(f"- {item}")
        print("")

    print("FINAL ANSWER")
    print("-" * 30)
    print(response["final_answer"])


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage:")
        print('python scripts\\run_user_agent.py text "I need 50 TVs..."')
        print("python scripts\\run_user_agent.py json data\\suppliers\\sample_shopping_request.json")
        print("python scripts\\run_user_agent.py files data\\documents\\sample_invoice.txt data\\documents\\sample_packing_list.txt")
        raise SystemExit(1)

    mode = sys.argv[1].lower()

    if mode == "text":
        text = " ".join(sys.argv[2:])
        response = run_user_agent_from_text(text)

    elif mode == "json":
        response = run_user_agent_from_json_file(Path(sys.argv[2]))

    elif mode == "files":
        paths = [Path(path) for path in sys.argv[2:]]
        response = run_user_agent_from_files(paths)

    else:
        raise SystemExit(f"Unknown mode: {mode}")

    _print_response(response)


if __name__ == "__main__":
    main()
