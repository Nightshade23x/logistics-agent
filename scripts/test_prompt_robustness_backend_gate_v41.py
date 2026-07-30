from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from app.llm_request_interpreter import (
    InterpretationResult,
    normalize_human_text,
    run_backend_with_interpreter,
    should_attempt_llm,
)


@contextmanager
def environment(**values):
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def test_live_failure_typos_are_normalized():
    text, corrections = normalize_human_text(
        "shp 10 crats ceramic tils frm India to Germany CIF each crat 1.2m x 1.0m x .8m wt 250kg fraglie stackble"
    )
    lower = text.lower()
    for expected in ("ship", "crates", "tiles", "from", "crate", "weight", "fragile", "stackable"):
        require(expected in lower, f"missing normalized word: {expected}; got {text}")
    require(corrections, "expected typo corrections")
    print("PASS - live typo vocabulary is normalized")


def test_loose_and_imperial_dimensions_gain_separators():
    metric, _ = normalize_human_text(
        "each palet 1.2 m 1.0 m 1.5 m weighs 180 kg fragle dont stack"
    )
    reordered, _ = normalize_human_text(
        "dimensions 100cm 80cm 60cm quantity 12"
    )
    imperial, _ = normalize_human_text(
        "each crate 4 ft by 3 ft by 2 ft weighs 120 lb"
    )
    require("1.2 m x 1.0 m x 1.5 m" in metric, metric)
    require("100cm x 80cm x 60cm" in reordered, reordered)
    require("4 ft x 3 ft x 2 ft" in imperial, imperial)
    require("do not stack" in metric.lower(), metric)
    print("PASS - loose metric and imperial dimensions become parser-friendly")


def test_physical_shipment_wrong_route_triggers_llm():
    prompt = "fragile but stackable ceramic tiles each crate weighs 90kg dimensions 100cm 80cm 60cm quantity 12 destination France origin India use FOB"
    weak = {
        "detected_intent": "shopping",
        "status": "needs_more_information",
        "agents_called": ["shopping_agent"],
    }
    # The patch runner disables live LLM calls globally while testing. Override
    # only the gate decision here so this unit test exercises fallback logic
    # without making a provider request.
    with environment(LLM_INTERPRETER_MODE="fallback"):
        attempt, reason = should_attempt_llm(prompt, weak, [])
    require(attempt, f"physical shipment should trigger interpreter; reason={reason}")
    require(reason in {"physical_shipment_misrouted", "physical_shipment_metrics_missing"}, reason)
    print("PASS - misrouted physical shipment triggers the LLM fallback")


def test_off_mode_is_fully_transparent():
    prompt = (
        "Ship 10 ceramic tile crates from India to Germany. "
        "Each crate weighs 220.462 lb and total volume is 10 CBM."
    )
    calls = []

    def deterministic(text):
        calls.append(text)
        return {
            "detected_intent": "logistics",
            "status": "review_required",
            "agents_called": ["logistics_agent"],
            "logistics_metrics": {"total_cbm": 10, "total_weight_kg": 1000.0},
            "request_metadata": {"input_source": text},
        }

    with environment(LLM_INTERPRETER_MODE="off"):
        result = run_backend_with_interpreter(prompt, deterministic)

    require(calls == [prompt], f"off mode changed deterministic input: {calls}")
    require(result["request_interpretation"]["reason"] == "disabled", result)
    require(result["request_interpretation"]["effective_text"] == prompt, result)
    require(result["logistics_metrics"]["total_weight_kg"] == 1000.0, result)
    print("PASS - off mode is transparent to legacy deterministic parsing")


def test_backend_boundary_reruns_and_exposes_metadata():
    calls = []

    def deterministic(text):
        calls.append(text)
        if "from India to Germany" in text and "1.2 m x 1.0 m x 0.8 m" in text:
            return {
                "detected_intent": "logistics",
                "status": "review_required",
                "agents_called": ["logistics_agent"],
                "logistics_metrics": {"total_cbm": 9.6, "total_weight_kg": 2500.0},
                "request_metadata": {"input_source": text},
            }
        return {
            "detected_intent": "unknown",
            "status": "needs_more_information",
            "agents_called": [],
            "request_metadata": {"input_source": text},
        }

    def interpreter(original, local):
        return InterpretationResult(
            original_text=original,
            effective_text=(
                "Ship 10 crates of ceramic tiles from India to Germany using CIF. "
                "Each crate is 1.2 m x 1.0 m x 0.8 m and weighs 250 kg. "
                "The cargo is fragile and stackable."
            ),
            attempted_llm=True,
            used_llm=True,
            provider="fake",
            model="test-model",
            confidence=0.98,
            reason="validated_llm_rewrite",
        )

    with environment(LLM_INTERPRETER_MODE="always"):
        result = run_backend_with_interpreter(
            "shp 10 crats ceramic tils frm India to Germany CIF each crat 1.2m x 1.0m x .8m wt 250kg fraglie stackble",
            deterministic,
            interpreter=interpreter,
        )

    require(result["detected_intent"] == "logistics", result)
    require(result["logistics_metrics"]["total_cbm"] == 9.6, result)
    require(result["request_interpretation"]["used_llm"] is True, result)
    require("effective_text" in result["request_interpretation"], result)
    require(result["request_metadata"]["input_source"].startswith("shp 10"), result)
    require(len(calls) == 1, f"obvious typo path should run only interpreted backend once; calls={calls}")
    print("PASS - final backend boundary uses the interpreted request and exposes diagnostics")


def test_real_backend_wrapper_is_outermost_without_live_llm():
    source = Path("app/backend_service.py").read_text(encoding="utf-8-sig")
    require("PROMPT_ROBUSTNESS_BACKEND_GATE_V41" in source, "backend V41 marker missing")

    from app.backend_service import process_text_request

    with environment(LLM_INTERPRETER_MODE="off"):
        payload = process_text_request(
            "Ship 1 crate of ceramic tiles from India to Germany. Each crate is 1 m x 1 m x 1 m and weighs 20 kg."
        )
    require(isinstance(payload.get("request_interpretation"), dict), payload.keys())
    require(payload["request_interpretation"]["reason"] == "disabled", payload["request_interpretation"])
    require(payload["request_interpretation"]["effective_text"], payload["request_interpretation"])
    print("PASS - real API backend path is wrapped and observable")


def main():
    test_live_failure_typos_are_normalized()
    test_loose_and_imperial_dimensions_gain_separators()
    test_physical_shipment_wrong_route_triggers_llm()
    test_off_mode_is_fully_transparent()
    test_backend_boundary_reruns_and_exposes_metadata()
    test_real_backend_wrapper_is_outermost_without_live_llm()
    print("All V41 prompt robustness backend-gate tests passed.")


if __name__ == "__main__":
    main()
