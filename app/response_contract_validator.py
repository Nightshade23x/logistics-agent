from __future__ import annotations

from typing import Any


KNOWN_AGENT_STATUSES = {
    "ready_for_review",
    "review_required",
    "needs_more_information",
    "partial_plan_needs_more_information",
    "blocked",
    "critical_review_required",
    "error",
    "not_configured",
    "not_implemented",
    "partner_review_not_configured",
    "clear",
}


REQUIRED_AGENT_FIELDS = [
    "agent_name",
    "status",
    "summary",
]


REQUIRED_USER_AGENT_FIELDS = [
    "agent_name",
    "status",
    "summary",
    "detected_intent",
    "agents_called",
    "specialist_responses",
    "final_verdict",
]


def _result(context: str, errors: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "context": context,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_agent_response(response: dict[str, Any], context: str = "agent_response") -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(response, dict):
        return _result(context, ["Response must be a dictionary."], [])

    for field in REQUIRED_AGENT_FIELDS:
        if field not in response:
            errors.append(f"Missing required field: {field}")

    agent_name = response.get("agent_name")
    status = response.get("status")
    summary = response.get("summary")

    if "agent_name" in response and not isinstance(agent_name, str):
        errors.append("agent_name must be a string.")

    if "status" in response and not isinstance(status, str):
        errors.append("status must be a string.")

    if isinstance(status, str) and status not in KNOWN_AGENT_STATUSES:
        warnings.append(f"Unknown status value: {status}")

    if "summary" in response and not isinstance(summary, str):
        errors.append("summary must be a string.")

    if isinstance(summary, str) and not summary.strip():
        warnings.append("summary is empty.")

    return _result(context, errors, warnings)


def validate_user_agent_response(response: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(response, dict):
        return _result("user_agent_response", ["Response must be a dictionary."], [])

    base_result = validate_agent_response(response, context="user_agent_response")
    errors.extend(base_result["errors"])
    warnings.extend(base_result["warnings"])

    for field in REQUIRED_USER_AGENT_FIELDS:
        if field not in response:
            errors.append(f"Missing required user agent field: {field}")

    if "agents_called" in response and not isinstance(response.get("agents_called"), list):
        errors.append("agents_called must be a list.")

    if "specialist_responses" in response and not isinstance(response.get("specialist_responses"), dict):
        errors.append("specialist_responses must be a dictionary.")

    if "final_verdict" in response and not isinstance(response.get("final_verdict"), dict):
        errors.append("final_verdict must be a dictionary.")

    specialist_responses = response.get("specialist_responses", {})

    if isinstance(specialist_responses, dict):
        for agent_name, agent_response in specialist_responses.items():
            if isinstance(agent_response, dict):
                specialist_result = validate_agent_response(
                    agent_response,
                    context=f"specialist_responses.{agent_name}",
                )
                for error in specialist_result["errors"]:
                    errors.append(f"{agent_name}: {error}")
                for warning in specialist_result["warnings"]:
                    warnings.append(f"{agent_name}: {warning}")
            else:
                errors.append(f"{agent_name}: specialist response must be a dictionary.")

    return _result("user_agent_response", errors, warnings)
