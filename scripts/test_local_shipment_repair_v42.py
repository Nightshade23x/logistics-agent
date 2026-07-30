from __future__ import annotations

import json
import os
from contextlib import contextmanager


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


def close(actual, expected, tolerance):
    return actual is not None and abs(float(actual) - float(expected)) <= tolerance


def test_live_physical_prompt_repairs():
    from app import backend_service

    cases = [
        (
            "shp 10 crats ceramic tils frm India to Germany CIF each crat 1.2m x 1.0m x .8m wt 250kg fraglie stackble",
            9.6,
            2500.0,
            10,
        ),
        (
            "need send 8 palets glass jars from India to USA CIF each palet 1.2 m 1.0 m 1.5 m weighs 180 kg fragle dont stack",
            14.4,
            1440.0,
            8,
        ),
        (
            "fragile but stackable ceramic tiles each crate weighs 90kg dimensions 100cm 80cm 60cm quantity 12 destination France origin India use FOB",
            5.76,
            1080.0,
            12,
        ),
        (
            "send 6 wooden crates Canada to Germany each 4 ft by 3 ft by 2 ft weighs 120 lb stackable",
            4.077604,
            326.586506,
            6,
        ),
        (
            "ship India to Germany CIF 4 crates ceramic tiles each 1m x 1m x 1m 200kg fragile stackable and 3 pallets pillows each 1.2m x 1m x 1.5m 80kg not fragile stackable",
            9.4,
            1040.0,
            7,
        ),
    ]

    with environment(LLM_INTERPRETER_MODE="fallback", LLM_INTERPRETER_TIMEOUT_SECONDS="1"):
        for prompt, expected_cbm, expected_weight, expected_units in cases:
            payload = backend_service.process_text_request(prompt, include_raw_response=False)
            metrics = payload.get("logistics_metrics") or {}
            interpretation = payload.get("request_interpretation") or {}
            structured = interpretation.get("structured_shipment") or {}

            require(payload.get("detected_intent") == "logistics", payload)
            require(close(metrics.get("total_cbm"), expected_cbm, 0.02), metrics)
            require(close(metrics.get("total_weight_kg"), expected_weight, 0.02), metrics)
            require(int(metrics.get("cargo_units") or 0) == expected_units, metrics)
            require(interpretation.get("reason") == "local_structured_repair", interpretation)
            require(interpretation.get("attempted_llm") is False, interpretation)
            require(int(structured.get("cargo_units") or 0) == expected_units, structured)

    print("PASS - all five failed live physical prompts are repaired locally without Gemini")


def test_gemini_resilience_configuration():
    from app import llm_request_interpreter as module

    require(module.DEFAULT_TIMEOUT_SECONDS >= 30.0, module.DEFAULT_TIMEOUT_SECONDS)
    require(module.CIRCUIT_BREAK_SECONDS <= 30.0, module.CIRCUIT_BREAK_SECONDS)
    source = open(module.__file__, "r", encoding="utf-8").read()
    require("retry_delays = (0.0, 1.0, 2.0)" in source, "retry backoff missing")
    require("http_" in source and "circuit_open_" in source, "provider diagnostics missing")
    print("PASS - Gemini uses longer timeouts, bounded retries and useful failure reasons")


def main():
    test_live_physical_prompt_repairs()
    test_gemini_resilience_configuration()
    print("All V42 local shipment repair and Gemini resilience tests passed.")


if __name__ == "__main__":
    main()
