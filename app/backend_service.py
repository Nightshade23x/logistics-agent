from __future__ import annotations

from pathlib import Path
from typing import Any

from app.action_plan_builder import build_action_plan
from app.booking_readiness_advisor import build_booking_readiness
from app.clarification_questions import build_clarification_questions
from app.document_quality_review import build_document_quality_review
from app.document_requirements_advisor import build_document_requirements_advice
from app.final_answer_builder import build_final_answer
from app.frontend_payload import build_frontend_payload
from app.insurance_advisor import build_insurance_advice
from app.landed_cost_advisor import build_landed_cost_advice
from app.logistics_quality_review import build_logistics_quality_review
from app.response_contract_validator import validate_user_agent_response
from app.shopping_quality_review import build_shopping_quality_review
from app.trade_terms_advisor import build_trade_terms_advice
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


def _attach_request_metadata(
    payload: dict[str, Any],
    request_type: str,
    input_source: Any,
    include_raw_response: bool,
) -> dict[str, Any]:
    payload["request_metadata"] = {
        "request_type": request_type,
        "input_source": input_source,
        "include_raw_response": include_raw_response,
        "served_by": "backend_service",
    }

    return payload


def _build_backend_payload(
    raw_response: dict[str, Any],
    request_type: str,
    input_source: Any,
    include_raw_response: bool = False,
) -> dict[str, Any]:
    payload = build_frontend_payload(
        raw_response,
        include_raw_response=include_raw_response,
    )

    payload = _attach_backend_validation(payload, raw_response)
    payload["shopping_quality_review"] = build_shopping_quality_review(raw_response)
    payload["logistics_quality_review"] = build_logistics_quality_review(raw_response)
    payload["document_quality_review"] = build_document_quality_review(raw_response)
    payload["trade_terms_advice"] = build_trade_terms_advice(
        raw_response,
        request_text=str(input_source) if request_type == "text" else None,
    )
    payload["insurance_advice"] = build_insurance_advice(
        {
            **raw_response,
            "trade_terms_advice": payload.get("trade_terms_advice"),
        }
    )
    payload["document_requirements_advice"] = build_document_requirements_advice(
        {
            **raw_response,
            "trade_terms_advice": payload.get("trade_terms_advice"),
            "insurance_advice": payload.get("insurance_advice"),
            "logistics_quality_review": payload.get("logistics_quality_review"),
            "document_quality_review": payload.get("document_quality_review"),
        }
    )
    payload["landed_cost_advice"] = build_landed_cost_advice(
        {
            **raw_response,
            "trade_terms_advice": payload.get("trade_terms_advice"),
            "logistics_quality_review": payload.get("logistics_quality_review"),
        }
    )
    payload["clarification_questions"] = build_clarification_questions(raw_response)
    payload["booking_readiness"] = build_booking_readiness(payload)

    trade_terms_advice = payload.get("trade_terms_advice", {})
    if isinstance(trade_terms_advice, dict):
        origin_confirmed = bool(trade_terms_advice.get("origin_country"))
        destination_confirmed = bool(trade_terms_advice.get("destination_country"))

        filtered_questions = []
        for question in payload["clarification_questions"]:
            question_text = str(question).lower()

            if destination_confirmed and "destination country" in question_text:
                continue

            if origin_confirmed and (
                "origin country" in question_text
                or "supplier country" in question_text
            ):
                continue

            filtered_questions.append(question)

        payload["clarification_questions"] = filtered_questions

    payload["final_answer"] = build_final_answer(payload)
    payload["action_plan"] = build_action_plan(payload)
    payload = _attach_request_metadata(
        payload=payload,
        request_type=request_type,
        input_source=input_source,
        include_raw_response=include_raw_response,
    )

    return payload


def _build_error_payload(
    request_type: str,
    input_source: Any,
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
        "shopping_quality_review": {
            "applicable": False,
            "status": "not_applicable",
            "summary": "Shopping quality review is not available because the backend request failed.",
            "selected_items_count": 0,
            "warnings": [],
            "blockers": [],
            "recommendations": [],
        },
        "logistics_quality_review": {
            "applicable": False,
            "status": "not_applicable",
            "summary": "Logistics quality review is not available because the backend request failed.",
            "warnings": [],
            "blockers": [],
            "recommendations": [],
        },
        "document_quality_review": {
            "applicable": False,
            "status": "not_applicable",
            "summary": "Document quality review is not available because the backend request failed.",
            "warnings": [],
            "blockers": [],
            "recommendations": [],
        },
        "trade_terms_advice": {
            "applicable": False,
            "status": "not_applicable",
            "summary": "Trade terms advice is not available because the backend request failed.",
            "incoterm": None,
            "warnings": [],
            "blockers": [],
            "recommendations": [],
            "user_questions": [],
        },
        "insurance_advice": {
            "applicable": False,
            "status": "not_applicable",
            "summary": "Insurance advice is not available because the backend request failed.",
            "insurance_recommendation": None,
            "warnings": [],
            "blockers": [],
            "recommendations": [],
        },
        "document_requirements_advice": {
            "applicable": False,
            "status": "not_applicable",
            "summary": "Document requirements advice is not available because the backend request failed.",
            "required_documents": [],
            "conditional_documents": [],
            "missing_or_unconfirmed_documents": [],
            "warnings": [],
            "recommendations": [],
            "user_questions": [],
        },
        "landed_cost_advice": {
            "applicable": False,
            "status": "not_applicable",
            "summary": "Landed cost advice is not available because the backend request failed.",
            "known_inputs": {},
            "missing_cost_inputs": [],
            "blockers": [],
            "warnings": [],
            "recommendations": [],
        },
        "clarification_questions": [],
        "final_answer": {
            "status": "blocked",
            "headline": "Request failed before the agent workflow could complete.",
            "answer_text": "The backend service could not process this request.",
            "ready_items": [],
            "blockers": [],
            "warnings": [],
            "next_actions": ["Review the backend error message and retry the request."],
        },
        "action_plan": {
            "status": "resolve_blockers",
            "summary": "Resolve backend error before continuing.",
            "immediate_actions": ["Review the backend error message and retry the request."],
            "before_booking": [],
            "partner_steps": [],
            "user_questions": [],
            "ready_to_continue": [],
        },
        "booking_readiness": {
            "applicable": False,
            "status": "blocked",
            "summary": "Booking readiness is not available because the backend request failed.",
            "score": 0,
            "ready_for_first_pass": False,
            "ready_for_booking": False,
            "next_gate": "backend_error",
            "blockers": ["Backend request failed."],
            "missing_information": [],
            "review_items": [],
            "ready_items": [],
            "next_steps": ["Review the backend error message and retry the request."],
        },
        "backend_validation": {
            "response_contract_valid": False,
            "response_contract_errors": [error_message],
            "response_contract_warnings": [],
        },
        "request_metadata": {
            "request_type": request_type,
            "input_source": input_source,
            "include_raw_response": include_raw_response,
            "served_by": "backend_service",
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
        return _build_backend_payload(
            raw_response=raw_response,
            request_type="text",
            input_source=user_text,
            include_raw_response=include_raw_response,
        )
    except Exception as error:
        return _build_error_payload(
            request_type="text",
            input_source=user_text,
            error=error,
            include_raw_response=include_raw_response,
        )


def process_json_file_request(
    json_path: str | Path,
    include_raw_response: bool = False,
) -> dict[str, Any]:
    path = Path(json_path)

    try:
        raw_response = run_user_agent_from_json_file(path)
        return _build_backend_payload(
            raw_response=raw_response,
            request_type="json_file",
            input_source=str(path),
            include_raw_response=include_raw_response,
        )
    except Exception as error:
        return _build_error_payload(
            request_type="json_file",
            input_source=str(path),
            error=error,
            include_raw_response=include_raw_response,
        )


def process_document_files_request(
    file_paths: list[str | Path],
    include_raw_response: bool = False,
) -> dict[str, Any]:
    paths = [Path(file_path) for file_path in file_paths]

    try:
        raw_response = run_user_agent_from_files(paths)
        return _build_backend_payload(
            raw_response=raw_response,
            request_type="document_files",
            input_source=[str(path) for path in paths],
            include_raw_response=include_raw_response,
        )
    except Exception as error:
        return _build_error_payload(
            request_type="document_files",
            input_source=[str(path) for path in paths],
            error=error,
            include_raw_response=include_raw_response,
        )
