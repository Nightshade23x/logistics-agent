from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

TEST_COMMANDS = [
    [sys.executable, "scripts/test_partner_adapters.py"],
    [sys.executable, "scripts/test_partner_config.py"],
    [sys.executable, "scripts/test_backend_status.py"],
    [sys.executable, "scripts/test_response_contract_validator.py"],
    [sys.executable, "scripts/test_partner_review_service.py"],
    [sys.executable, "scripts/test_partner_review_payload_validator.py"],
    [sys.executable, "scripts/test_partner_request_builder.py"],
    [sys.executable, "scripts/test_partner_review_request_builder_integration.py"],
    [sys.executable, "scripts/test_final_verdict.py"],
    [sys.executable, "scripts/test_frontend_payload.py"],
    [sys.executable, "scripts/test_backend_service.py"],
    [sys.executable, "scripts/test_user_agent.py"],
    [sys.executable, "scripts/test_shopping_agent.py"],
    [sys.executable, "scripts/test_document_agent.py"],
    [sys.executable, "scripts/test_logistics_agent.py"],
    [sys.executable, "scripts/system_health_check.py"],
]


def main() -> None:
    print("RUNNING FULL LOCAL TEST SUITE")
    print("=" * 40)

    failed_commands = []

    for command in TEST_COMMANDS:
        command_text = " ".join(command)
        print("")
        print(f"> {command_text}")
        print("-" * 40)

        result = subprocess.run(command, cwd=ROOT_DIR)

        if result.returncode != 0:
            failed_commands.append(command_text)

    print("")
    print("=" * 40)

    if failed_commands:
        print("FAILED TEST COMMANDS")
        for command in failed_commands:
            print(f"- {command}")
        raise SystemExit(1)

    print("All tests passed.")


if __name__ == "__main__":
    main()
