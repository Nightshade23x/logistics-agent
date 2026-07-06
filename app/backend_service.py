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


def process_text_request(
    user_text: str,
    include_raw_response: bool = False,
) -> dict[str, Any]:
    raw_response = run_user_agent_from_text(user_text)
    return _build_backend_payload(raw_response, include_raw_response=include_raw_response)


def process_json_file_request(
    json_path: str | Path,
    include_raw_response: bool = False,
) -> dict[str, Any]:
    raw_response = run_user_agent_from_json_file(Path(json_path))
    return _build_backend_payload(raw_response, include_raw_response=include_raw_response)


def process_document_files_request(
    file_paths: list[str | Path],
    include_raw_response: bool = False,
) -> dict[str, Any]:
    paths = [Path(file_path) for file_path in file_paths]
    raw_response = run_user_agent_from_files(paths)
    return _build_backend_payload(raw_response, include_raw_response=include_raw_response)
