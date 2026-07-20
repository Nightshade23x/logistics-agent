from __future__ import annotations

from typing import Any


VALID_INTENTS = {"shopping", "document", "logistics", "unknown"}
VALID_AGENTS = {"shopping_agent", "document_ai_agent", "logistics_agent"}
VALID_INPUT_TYPES = {"text", "files", "json"}
VALID_CONFIDENCE = {"low", "medium", "high"}


def validate_router_decision(decision: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if decision.get("intent") not in VALID_INTENTS:
        errors.append(f"invalid_intent:{decision.get('intent')}")

    agents = decision.get("agents_to_call")
    if not isinstance(agents, list):
        errors.append("agents_to_call_not_list")
    else:
        for agent in agents:
            if agent not in VALID_AGENTS:
                errors.append(f"invalid_agent:{agent}")

    if decision.get("input_type") not in VALID_INPUT_TYPES:
        errors.append(f"invalid_input_type:{decision.get('input_type')}")

    if not isinstance(decision.get("missing_information", []), list):
        errors.append("missing_information_not_list")

    if decision.get("confidence") not in VALID_CONFIDENCE:
        errors.append(f"invalid_confidence:{decision.get('confidence')}")

    if not isinstance(decision.get("reason"), str):
        errors.append("reason_missing_or_invalid")

    return errors


def is_valid_router_decision(decision: dict[str, Any]) -> bool:
    return not validate_router_decision(decision)
