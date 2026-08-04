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


def display_weight(payload: dict[str, Any]) -> dict[str, Any]:
    display = payload.get("display_measurements")
    if not isinstance(display, dict):
        return {}

    weight = display.get("weight")
    return weight if isinstance(weight, dict) else {}


def metadata(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("request_metadata")
    return value if isinstance(value, dict) else {}


def test_explicit_total_precision() -> None:
    payload = process_text_request(
        "Ship 10 CBM of ceramic tiles from India to USA. "
        "Total weight is 2204.62 lb.",
        include_raw_response=False,
    )

    require(
        metrics(payload).get("total_weight_kg") == 1000,
        metrics(payload),
    )

    weight = display_weight(payload)
    require(
        weight.get("total_weight") == 2204.62,
        weight,
    )
    require(
        weight.get("display_unit") == "lb",
        weight,
    )

    info = metadata(payload).get(
        "explicit_imperial_total_weight_precision_v79"
    )
    require(isinstance(info, dict), metadata(payload))
    require(
        info.get("canonical_total_weight_kg") == 1000,
        info,
    )

    print(
        "PASS - 2204.62 lb remains displayed while "
        "the canonical total is 1000 kg"
    )


def test_non_near_integer_is_not_forced() -> None:
    payload = process_text_request(
        "Ship 1 CBM of ceramic tiles from India to USA. "
        "Total weight is 100 lb.",
        include_raw_response=False,
    )

    total = metrics(payload).get("total_weight_kg")
    require(total is not None, metrics(payload))
    require(total != 45, metrics(payload))

    require(
        "explicit_imperial_total_weight_precision_v79"
        not in metadata(payload),
        metadata(payload),
    )

    print(
        "PASS - ordinary non-near-integer pound conversions "
        "are not rounded to a whole kilogram"
    )


def test_per_package_weight_is_not_touched() -> None:
    payload = process_text_request(
        "Ship 1 crate of ceramic tiles from India to Germany. "
        "Each crate weighs 250 lb and measures 1 m x 1 m x 1 m.",
        include_raw_response=False,
    )

    require(
        "explicit_imperial_total_weight_precision_v79"
        not in metadata(payload),
        metadata(payload),
    )

    weight = display_weight(payload)
    require(
        weight.get("total_weight") == 250,
        weight,
    )
    require(
        weight.get("display_unit") == "lb",
        weight,
    )

    print(
        "PASS - per-package pound handling remains unchanged"
    )


def main() -> None:
    test_explicit_total_precision()
    test_non_near_integer_is_not_forced()
    test_per_package_weight_is_not_touched()
    print(
        "All V79 explicit imperial total precision checks passed."
    )


if __name__ == "__main__":
    main()
