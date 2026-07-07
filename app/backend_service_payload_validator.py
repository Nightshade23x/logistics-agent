from __future__ import annotations

from typing import Any


REQUIRED_BACKEND_PAYLOAD_FIELDS = [
    "agent_name",
    "status",
    "decision",
    "summary",
    "short_answer",
    "final_verdict",
    "agents_called",
    "logistics_metrics",
    "partner_review_status",
    "missing_information_count",
    "assumptions_count",
    "agent_summaries",
    "shopping_quality_review",
    "logistics_quality_review",
    "document_quality_review",
    "trade_terms_advice",
    "insurance_advice",
    "document_requirements_advice",
    "landed_cost_advice",
    "clarification_questions",
    "final_answer",
    "action_plan",
    "backend_validation",
    "request_metadata",
]


REQUIRED_BACKEND_VALIDATION_FIELDS = [
    "response_contract_valid",
    "response_contract_errors",
    "response_contract_warnings",
]


REQUIRED_REQUEST_METADATA_FIELDS = [
    "request_type",
    "input_source",
    "include_raw_response",
    "served_by",
]


def validate_backend_service_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(payload, dict):
        return {
            "is_valid": False,
            "errors": ["Backend service payload must be a dictionary."],
            "warnings": [],
        }

    for field in REQUIRED_BACKEND_PAYLOAD_FIELDS:
        if field not in payload:
            errors.append(f"Missing required backend payload field: {field}")

    if "agents_called" in payload and not isinstance(payload["agents_called"], list):
        errors.append("agents_called must be a list.")

    if "final_verdict" in payload and not isinstance(payload["final_verdict"], dict):
        errors.append("final_verdict must be a dictionary.")

    if "logistics_metrics" in payload and not isinstance(payload["logistics_metrics"], dict):
        errors.append("logistics_metrics must be a dictionary.")

    if "agent_summaries" in payload and not isinstance(payload["agent_summaries"], list):
        errors.append("agent_summaries must be a list.")

    if "clarification_questions" in payload and not isinstance(payload["clarification_questions"], list):
        errors.append("clarification_questions must be a list.")

    if "shopping_quality_review" in payload and not isinstance(payload["shopping_quality_review"], dict):
        errors.append("shopping_quality_review must be a dictionary.")

    if "logistics_quality_review" in payload and not isinstance(payload["logistics_quality_review"], dict):
        errors.append("logistics_quality_review must be a dictionary.")

    if "document_quality_review" in payload and not isinstance(payload["document_quality_review"], dict):
        errors.append("document_quality_review must be a dictionary.")

    if "trade_terms_advice" in payload and not isinstance(payload["trade_terms_advice"], dict):
        errors.append("trade_terms_advice must be a dictionary.")

    if "insurance_advice" in payload and not isinstance(payload["insurance_advice"], dict):
        errors.append("insurance_advice must be a dictionary.")

    if "document_requirements_advice" in payload and not isinstance(payload["document_requirements_advice"], dict):
        errors.append("document_requirements_advice must be a dictionary.")

    if "landed_cost_advice" in payload and not isinstance(payload["landed_cost_advice"], dict):
        errors.append("landed_cost_advice must be a dictionary.")

    if "final_answer" in payload and not isinstance(payload["final_answer"], dict):
        errors.append("final_answer must be a dictionary.")

    if "action_plan" in payload and not isinstance(payload["action_plan"], dict):
        errors.append("action_plan must be a dictionary.")

    backend_validation = payload.get("backend_validation", {})

    if not isinstance(backend_validation, dict):
        errors.append("backend_validation must be a dictionary.")
    else:
        for field in REQUIRED_BACKEND_VALIDATION_FIELDS:
            if field not in backend_validation:
                errors.append(f"Missing backend_validation field: {field}")

    request_metadata = payload.get("request_metadata", {})

    if not isinstance(request_metadata, dict):
        errors.append("request_metadata must be a dictionary.")
    else:
        for field in REQUIRED_REQUEST_METADATA_FIELDS:
            if field not in request_metadata:
                errors.append(f"Missing request_metadata field: {field}")

        if request_metadata.get("served_by") != "backend_service":
            warnings.append("request_metadata.served_by is not backend_service.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
