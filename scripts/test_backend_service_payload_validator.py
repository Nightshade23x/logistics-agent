from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.backend_service_payload_validator import validate_backend_service_payload


def test_valid_backend_service_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    result = validate_backend_service_payload(payload)

    assert result["is_valid"] is True
    assert result["errors"] == []


def test_valid_backend_service_error_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "missing_file.json"
    )

    result = validate_backend_service_payload(payload)

    assert result["is_valid"] is True
    assert result["errors"] == []
    assert payload["status"] == "error"
    assert payload["decision"] == "blocked"


def test_invalid_backend_service_payload_missing_fields():
    payload = {
        "agent_name": "backend_service",
        "status": "error",
    }

    result = validate_backend_service_payload(payload)

    assert result["is_valid"] is False
    assert "Missing required backend payload field: decision" in result["errors"]
    assert "Missing required backend payload field: request_metadata" in result["errors"]


def main() -> None:
    test_valid_backend_service_payload()
    test_valid_backend_service_error_payload()
    test_invalid_backend_service_payload_missing_fields()

    print("All backend service payload validator tests passed.")


if __name__ == "__main__":
    main()
