from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import (
    process_document_files_request,
    process_json_file_request,
    process_text_request,
)


def test_backend_service_json_request():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert payload["agent_name"] == "user_agent"
    assert payload["detected_intent"] == "shopping"
    assert payload["decision"] == "review_required"
    assert "shopping_agent" in payload["agents_called"]
    assert "logistics_agent" in payload["agents_called"]
    assert "partner_review_service" in payload["agents_called"]
    assert payload["backend_validation"]["response_contract_valid"] is True
    assert payload["request_metadata"]["request_type"] == "json_file"
    assert payload["request_metadata"]["served_by"] == "backend_service"
    assert payload["request_metadata"]["include_raw_response"] is False
    assert "sample_shopping_request.json" in payload["request_metadata"]["input_source"]
    assert "raw_response" not in payload


def test_backend_service_json_request_with_raw_response():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json",
        include_raw_response=True,
    )

    assert payload["backend_validation"]["response_contract_valid"] is True
    assert payload["request_metadata"]["include_raw_response"] is True
    assert payload["raw_response"]["agent_name"] == "user_agent"


def test_backend_service_document_request():
    payload = process_document_files_request(
        [
            ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
            ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
        ]
    )

    assert payload["agent_name"] == "user_agent"
    assert payload["detected_intent"] == "document"
    assert "document_ai_agent" in payload["agents_called"]
    assert "logistics_agent" in payload["agents_called"]
    assert "partner_review_service" in payload["agents_called"]
    assert payload["backend_validation"]["response_contract_valid"] is True
    assert payload["request_metadata"]["request_type"] == "document_files"
    assert len(payload["request_metadata"]["input_source"]) == 2


def test_backend_service_text_request():
    request_text = (
        "I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
        "Prefer suppliers from India. Avoid China. Budget 13000 USD."
    )

    payload = process_text_request(request_text)

    assert payload["agent_name"] == "user_agent"
    assert payload["detected_intent"] == "shopping"
    assert "shopping_agent" in payload["agents_called"]
    assert payload["backend_validation"]["response_contract_valid"] is True
    assert payload["request_metadata"]["request_type"] == "text"
    assert payload["request_metadata"]["input_source"] == request_text


def test_backend_service_returns_error_payload_for_missing_json_file():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "missing_file.json"
    )

    assert payload["agent_name"] == "backend_service"
    assert payload["status"] == "error"
    assert payload["decision"] == "blocked"
    assert payload["backend_validation"]["response_contract_valid"] is False
    assert payload["request_metadata"]["request_type"] == "json_file"
    assert payload["request_metadata"]["served_by"] == "backend_service"
    assert payload["error"]["request_type"] == "json_file"


def main() -> None:
    test_backend_service_json_request()
    test_backend_service_json_request_with_raw_response()
    test_backend_service_document_request()
    test_backend_service_text_request()
    test_backend_service_returns_error_payload_for_missing_json_file()

    print("All backend service tests passed.")


if __name__ == "__main__":
    main()
