from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.response_contract_validator import (
    validate_agent_response,
    validate_user_agent_response,
)
from app.user_agent import run_user_agent_from_json_file


def test_valid_basic_agent_response():
    response = {
        "agent_name": "test_agent",
        "status": "ready_for_review",
        "summary": "Test response is ready.",
    }

    result = validate_agent_response(response)

    assert result["is_valid"] is True
    assert result["errors"] == []


def test_invalid_basic_agent_response():
    response = {
        "agent_name": "broken_agent",
    }

    result = validate_agent_response(response)

    assert result["is_valid"] is False
    assert "Missing required field: status" in result["errors"]
    assert "Missing required field: summary" in result["errors"]


def test_user_agent_shopping_json_response_contract():
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    result = validate_user_agent_response(response)

    assert result["is_valid"] is True
    assert result["errors"] == []


def main() -> None:
    test_valid_basic_agent_response()
    test_invalid_basic_agent_response()
    test_user_agent_shopping_json_response_contract()

    print("All response contract validator tests passed.")


if __name__ == "__main__":
    main()
