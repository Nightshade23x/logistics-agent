from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)
os.environ["LLM_INTERPRETER_MODE"] = "off"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["GOOGLE_GENERATIVE_AI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from app.backend_service import process_text_request


def require(condition: bool, message: Any) -> None:
    if not condition:
        raise AssertionError(message)


def metrics(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("logistics_metrics")
    return value if isinstance(value, dict) else {}


def validation(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("input_validation_v44")
    return value if isinstance(value, dict) else {}


def display_weight(payload: dict[str, Any]) -> dict[str, Any]:
    display = payload.get("display_measurements")
    if not isinstance(display, dict):
        return {}

    weight = display.get("weight")
    return weight if isinstance(weight, dict) else {}


def find_invalid_totals(
    value: Any,
    path: str = "$",
) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            if key in {
                "total_weight_kg",
                "display_total_weight",
            } and child is not None:
                found.append((child_path, child))

            if key == "weight_known" and child is True:
                found.append((child_path, child))

            found.extend(find_invalid_totals(child, child_path))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(
                find_invalid_totals(
                    child,
                    f"{path}[{index}]",
                )
            )

    return found


def check_invalid(prompt: str, expected_quantity: int) -> None:
    payload = process_text_request(
        prompt,
        include_raw_response=False,
    )

    current_metrics = metrics(payload)
    current_validation = validation(payload)

    require(
        current_metrics.get("total_cbm") is None,
        current_metrics,
    )
    require(
        current_metrics.get("total_weight_kg") is None,
        current_metrics,
    )
    require(
        current_validation.get("errors"),
        current_validation,
    )
    require(
        payload.get("decision") == "review_required",
        payload.get("decision"),
    )

    facts = current_validation.get("authoritative_facts")
    require(isinstance(facts, dict), current_validation)
    require(facts.get("quantity") == expected_quantity, facts)

    invalid_totals = find_invalid_totals(payload)
    require(not invalid_totals, invalid_totals)

    weight = display_weight(payload)
    if weight:
        require(weight.get("package_count") == expected_quantity, weight)
        require(weight.get("total_weight") is None, weight)

    metadata = payload.get("request_metadata")
    require(isinstance(metadata, dict), metadata)

    guard = metadata.get(
        "final_nonpositive_quantity_weight_authority_v78"
    )
    require(isinstance(guard, dict), metadata)
    require(guard.get("status") == "applied", guard)
    require(
        guard.get("authoritative_quantity") == expected_quantity,
        guard,
    )


def check_valid_control() -> None:
    payload = process_text_request(
        "Ship 1 pallet of ceramic tiles from India to Germany. "
        "Each pallet weighs 500 kg and measures 1.2 m x 1 m x 1.4 m.",
        include_raw_response=False,
    )

    current_metrics = metrics(payload)
    require(
        current_metrics.get("total_weight_kg") == 500,
        current_metrics,
    )

    weight = display_weight(payload)
    require(weight.get("package_count") == 1, weight)
    require(weight.get("total_weight") == 500, weight)

    metadata = payload.get("request_metadata")
    if isinstance(metadata, dict):
        require(
            "final_nonpositive_quantity_weight_authority_v78"
            not in metadata,
            metadata.get(
                "final_nonpositive_quantity_weight_authority_v78"
            ),
        )


def main() -> None:
    check_invalid(
        "Ship -5 crates of machinery from India to Germany. "
        "Each crate weighs -20 kg and measures-1 m x 1 m x 1 m.",
        -5,
    )
    print("PASS - negative quantity keeps shipment totals cleared")

    check_invalid(
        "Ship 0 pallets of ceramic tiles from India to Germany. "
        "Each pallet weighs 500 kg and measures 1.2 m x 1 m x 1.4 m.",
        0,
    )
    print("PASS - zero quantity cannot regain a shipment weight total")

    check_valid_control()
    print("PASS - valid one-package 500 kg shipment remains unchanged")

    print("All V78 final nonpositive quantity authority checks passed.")


if __name__ == "__main__":
    main()
