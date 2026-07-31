from __future__ import annotations

import json
import os
from contextlib import contextmanager

from app.llm_request_interpreter import (
    InterpretationResult,
    interpret_with_llm,
    normalize_human_text,
    run_with_interpreter,
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


def fake_transport(payload):
    def transport(**kwargs):
        return json.dumps(payload)
    return transport


def test_local_normalization():
    text, corrections = normalize_human_text(
        "shp 10 boxs of tiles,from India,to Germany;fraglie and stackble"
    )
    require("ship" in text.lower(), "ship typo was not normalized")
    require("fragile" in text.lower(), "fragile typo was not normalized")
    require("stackable" in text.lower(), "stackable typo was not normalized")
    require(corrections, "normalization corrections were not recorded")
    print("PASS - local punctuation and common logistics typos are normalized")


def test_validated_llm_rewrite():
    payload = {
        "normalized_text": "Ship 10 boxes of ceramic tiles from India to Germany. Each box weighs 25 kg. The cargo is fragile.",
        "intent": "logistics",
        "confidence": 0.96,
        "corrections": ["Corrected spelling and sentence order"],
        "ambiguities": [],
        "missing_fields": ["dimensions"],
        "shipment": {
            "origin": "India",
            "destination": "Germany",
            "incoterm": None,
            "budget": None,
            "transport_mode": None,
            "items": [{
                "name": "ceramic tiles",
                "quantity": 10,
                "package_type": "boxes",
                "unit_weight_kg": 25,
                "total_weight_kg": None,
                "total_cbm": None,
                "dimensions": None,
                "fragile": True,
                "stackable": None,
                "hazardous": None,
            }],
        },
    }
    original = "shp 10 boxs ceramic tiles india germany each 25 kg fraglie"
    local, _ = normalize_human_text(original)
    result = interpret_with_llm(original, local, transport=fake_transport(payload))
    require(result.used_llm, f"valid LLM rewrite was rejected: {result.reason}")
    require(result.confidence == 0.96, "confidence was not preserved")
    require(result.structured_shipment["destination"] == "Germany", "structured route was not validated")
    print("PASS - LLM output is schema-validated and accepted when facts are preserved")


def test_numeric_hallucination_guard():
    payload = {
        "normalized_text": "Ship 20 boxes from India to Germany. Each box weighs 25 kg.",
        "intent": "logistics",
        "confidence": 0.99,
        "corrections": [],
        "ambiguities": [],
        "missing_fields": [],
        "shipment": {"items": []},
    }
    original = "ship 10 boxes from India to Germany each box 25 kg"
    local, _ = normalize_human_text(original)
    result = interpret_with_llm(original, local, transport=fake_transport(payload))
    require(not result.used_llm, "rewrite that changed quantity was accepted")
    require(result.reason == "numeric_guard_rejected_rewrite", "numeric guard reason was not reported")
    print("PASS - LLM rewrites cannot add, remove, or change explicit numbers")


def test_hybrid_rerun_and_original_text():
    calls = []

    def deterministic_runner(text):
        calls.append(text)
        if text.startswith("Ship 10 boxes"):
            return {
                "status": "review_required",
                "detected_intent": "logistics",
                "agents_called": ["logistics_agent"],
                "missing_information": ["dimensions"],
                "logistics_metrics": {"total_weight_kg": 250},
                "request_metadata": {"input_source": text},
            }
        return {
            "status": "needs_more_information",
            "detected_intent": "unknown",
            "agents_called": [],
            "missing_information": ["clearer_request"],
            "request_metadata": {"input_source": text},
        }

    def interpreter(original, local):
        return InterpretationResult(
            original_text=original,
            effective_text="Ship 10 boxes of ceramic tiles from India to Germany. Each box weighs 25 kg. The cargo is fragile.",
            attempted_llm=True,
            used_llm=True,
            provider="fake",
            model="test-model",
            confidence=0.97,
            reason="validated_llm_rewrite",
        )

    original = "shp 10 boxs ceramic tiles india germany each 25 kg fraglie"
    with environment(LLM_INTERPRETER_MODE="fallback"):
        response = run_with_interpreter(original, deterministic_runner, interpreter=interpreter)

    require(len(calls) == 2, "hybrid pipeline did not rerun deterministic backend")
    require(response["detected_intent"] == "logistics", "better deterministic response was not selected")
    require(response["request_metadata"]["input_source"] == original, "original request was not preserved")
    require(response["request_metadata"]["interpretation_used_llm"] is True, "LLM usage was not visible")
    require(response["logistics_metrics"]["total_weight_kg"] == 250, "deterministic calculation was not retained")
    print("PASS - malformed text is repaired, then existing deterministic calculations remain authoritative")


def test_llm_failure_is_non_fatal():
    def deterministic_runner(text):
        return {
            "status": "review_required",
            "detected_intent": "logistics",
            "agents_called": ["logistics_agent"],
            "request_metadata": {"input_source": text},
        }

    def failed_interpreter(original, local):
        return InterpretationResult(
            original_text=original,
            effective_text=local,
            attempted_llm=True,
            used_llm=False,
            provider="gemini",
            reason="llm_unavailable:RuntimeError",
        )

    with environment(LLM_INTERPRETER_MODE="always"):
        response = run_with_interpreter("ship cargo from India to Germany", deterministic_runner, interpreter=failed_interpreter)
    require(response["detected_intent"] == "logistics", "LLM failure broke deterministic response")
    require(response["request_interpretation"]["used_llm"] is False, "failed LLM call was marked as used")
    print("PASS - quota, timeout, and provider failures fall back without breaking requests")


def main():
    test_local_normalization()
    test_validated_llm_rewrite()
    test_numeric_hallucination_guard()
    test_hybrid_rerun_and_original_text()
    test_llm_failure_is_non_fatal()
    print("All V40 LLM request interpreter tests passed.")


if __name__ == "__main__":
    main()
