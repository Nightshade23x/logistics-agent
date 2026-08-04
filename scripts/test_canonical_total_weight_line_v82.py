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

from app import backend_service
from api_server import app
from fastapi.testclient import TestClient


EXPECTED_LINE = "- Total weight: 1000 kg"


def require(condition: bool, message: Any) -> None:
    if not condition:
        raise AssertionError(message)


def assert_contract(payload: dict[str, Any]) -> None:
    metrics = payload.get("logistics_metrics")
    require(isinstance(metrics, dict), payload)
    require(metrics.get("total_weight_kg") == 1000, metrics)

    final_answer = payload.get("final_answer")
    require(isinstance(final_answer, dict), final_answer)

    answer_text = str(
        final_answer.get("answer_text") or ""
    )
    display_answer = str(
        payload.get("display_answer") or ""
    )
    frontend_answer = str(
        payload.get("frontend_answer") or ""
    )

    for label, text in (
        ("final_answer", answer_text),
        ("display_answer", display_answer),
        ("frontend_answer", frontend_answer),
    ):
        require(EXPECTED_LINE in text, (label, text))
        require("1000.0 kg" not in text, (label, text))


def main() -> None:
    imperial_prompt = (
        "Ship 10 crates from India to Port of Los Angeles. "
        "Each crate is 4 ft x 3 ft x 2 ft and weighs 220.462 lb. "
        "The crates are fragile and stackable."
    )
    metric_prompt = (
        "Ship 10 crates from India to Port of Los Angeles. "
        "Each crate is 1.2192 m x 0.9144 m x 0.6096 m "
        "and weighs 100 kg. "
        "The crates are fragile and stackable."
    )

    for prompt, label in (
        (imperial_prompt, "direct imperial"),
        (metric_prompt, "direct metric"),
    ):
        payload = backend_service.process_text_request(
            prompt,
            include_raw_response=False,
        )
        assert_contract(payload)
        print(f"PASS - {label} contract")

    client = TestClient(app)
    response = client.post(
        "/api/request/text",
        json={
            "user_text": imperial_prompt,
            "include_raw_response": False,
        },
    )
    require(response.status_code == 200, response.text)
    assert_contract(response.json())
    print("PASS - FastAPI imperial contract")

    print(
        "All V83 final weight text contract checks passed."
    )


if __name__ == "__main__":
    main()