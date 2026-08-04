from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["LLM_INTERPRETER_MODE"] = "off"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["GOOGLE_GENERATIVE_AI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

from app.backend_service import process_text_request


def require(condition: bool, message: Any) -> None:
    if not condition:
        raise AssertionError(message)


def metrics(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("logistics_metrics")
    return value if isinstance(value, dict) else {}


def metadata(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("request_metadata")
    return value if isinstance(value, dict) else {}


def main() -> None:
    per_unit = process_text_request(
        "Ship 10 crates from India to Port of Los Angeles. "
        "Each crate is 4 ft x 3 ft x 2 ft and weighs 220.462 lb. "
        "The crates are fragile and stackable.",
        include_raw_response=False,
    )

    require(
        metrics(per_unit).get("total_weight_kg") == 1000,
        metrics(per_unit),
    )

    info = metadata(per_unit).get(
        "practical_imperial_precision_v80"
    )
    require(isinstance(info, dict), metadata(per_unit))
    require(info.get("canonical_unit_kg") == 100, info)
    require(info.get("canonical_total_kg") == 1000, info)
    print("PASS - per-unit imperial practical precision is canonical")

    explicit_total = process_text_request(
        "Ship 10 CBM of ceramic tiles from India to USA. "
        "Total weight is 2204.62 lb.",
        include_raw_response=False,
    )

    require(
        metrics(explicit_total).get("total_weight_kg") == 1000,
        metrics(explicit_total),
    )
    print("PASS - explicit total imperial practical precision is canonical")

    ordinary = process_text_request(
        "Ship 1 crate of ceramic tiles from India to Germany. "
        "Each crate weighs 250 lb and measures 1 m x 1 m x 1 m.",
        include_raw_response=False,
    )

    require(
        "practical_imperial_precision_v80"
        not in metadata(ordinary),
        metadata(ordinary),
    )
    print("PASS - ordinary pound conversions are unchanged")

    print("All V80 practical imperial precision checks passed.")


if __name__ == "__main__":
    main()
