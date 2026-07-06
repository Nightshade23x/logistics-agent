from __future__ import annotations

from pathlib import Path
from typing import Any

from app.frontend_payload import build_frontend_payload
from app.response_contract_validator import validate_user_agent_response
from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json_file,
    run_user_agent_from_text,
)


def _attach_backend_validation(payload: dict[str, Any], raw_response: dict[str, Any]) -> dict[str, Any]:
    contract_result = validate_user_agent_response(raw_response)

    payload["backend_validation"] = {
        "response_contract_valid": contract_result["is_valid"],
        "response_contract_errors": contract_result["errors"],
        "response_contract_warnings": contract_result["warnings"],
    }

    return payload


def _build_backend_payload(
    raw_response: dict[str, Any],
    include_raw_response: bool = False,
) -> dict[str, Any]:
    payload = build_frontend_payload(
        raw_response,
        include_raw_response=include_raw_response,
    )

    return _attach_backend_validation(payload, raw_response)


def _build_error_payload(
    request_type: str,
    error: Exception,
    include_raw_response: bool = False,
) -> dict[str, Any]:
    error_message = str(error)
    error_type = type(error).__name__

    payload: dict[str, Any] = {
        "agent_name": "backend_service",
        "status": "error",
        "detected_intent": None,
        "agents_called": [],
        "summary": f"Backend service could not process {request_type} request.",
        "short_answer": f"Request failed: {error_message}",
        "final_verdict": {
            "verdict": "blocked",
            "agent_statuses": ["error"],
            "blockers": [error_message],
            "warnings": [],
            "missing_information_count": 0,
            "partner_review_status": None,
        },
        "decision": "blocked",
        "logistics_metrics": {},
        "partner_review_status": None,
        "partner_review_summary": None,
        "missing_information_count": 0,
        "missing_information_preview": [],
        "assumptions_count": 0,
        "assumptions_preview": [],
        "agent_summaries": [],
        "backend_validation": {
            "response_contract_valid": False,
            "response_contract_errors": [error_message],
            "response_contract_warnings": [],
        },
        "error": {
            "type": error_type,
            "message": error_message,
            "request_type": request_type,
        },
    }

    if include_raw_response:
        payload["raw_response"] = None

    return payload


def process_text_request(
    user_text: str,
    include_raw_response: bool = False,
) -> dict[str, Any]:
    try:
        raw_response = run_user_agent_from_text(user_text)
        return _build_backend_payload(raw_response, include_raw_response=include_raw_response)
    except Exception as error:
        return _build_error_payload(
            request_type="text",
            error=error,
            include_raw_response=include_raw_response,
        )


def process_json_file_request(
    json_path: str | Path,
    include_raw_response: bool = False,
) -> dict[str, Any]:
    try:
        raw_response = run_user_agent_from_json_file(Path(json_path))
        return _build_backend_payload(raw_response, include_raw_response=include_raw_response)
    except Exception as error:
        return _build_error_payload(
            request_type="json_file",
            error=error,
            include_raw_response=include_raw_response,
        )


def process_document_files_request(
    file_paths: list[str | Path],
    include_raw_response: bool = False,
) -> dict[str, Any]:
    try:
        paths = [Path(file_path) for file_path in file_paths]
        raw_response = run_user_agent_from_files(paths)
        return _build_backend_payload(raw_response, include_raw_response=include_raw_response)
    except Exception as error:
        return _build_error_payload(
            request_type="document_files",
            error=error,
            include_raw_response=include_raw_response,
        )
