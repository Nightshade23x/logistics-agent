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


def main() -> None:
    payload = process_text_request(
        "Ship 10 crates from India to Port of Los Angeles. "
        "Each crate is 4 ft x 3 ft x 2 ft and weighs 220.462 lb. "
        "The crates are fragile and stackable.",
        include_raw_response=False,
    )

    metrics = payload.get("logistics_metrics")
    require(isinstance(metrics, dict), payload)
    require(metrics.get("total_weight_kg") == 1000, metrics)

    final_answer = str(payload.get("final_answer") or "")
    require("1000 kg" in final_answer, final_answer)
    require("1000.0 kg" not in final_answer, final_answer)
    require("999.998811 kg" not in final_answer, final_answer)

    metadata = payload.get("request_metadata")
    require(isinstance(metadata, dict), payload)

    sync = metadata.get("practical_imperial_text_sync_v81")
    require(isinstance(sync, dict), metadata)
    require(sync.get("status") == "applied", sync)

    print(
        "PASS - canonical imperial weight is synchronized "
        "across numeric fields and user-facing answer text"
    )


if __name__ == "__main__":
    main()