from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app.llm_request_interpreter as module


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def valid_payload(normalized_text: str) -> str:
    return json.dumps(
        {
            "normalized_text": normalized_text,
            "intent": "logistics",
            "confidence": 0.92,
            "corrections": [],
            "ambiguities": [],
            "missing_fields": ["weight", "dimensions"],
            "shipment": {
                "origin": "India",
                "destination": "Germany",
                "incoterm": None,
                "budget": None,
                "transport_mode": None,
                "items": [
                    {
                        "name": "optical sensors",
                        "quantity": None,
                        "package_type": None,
                        "unit_weight_kg": None,
                        "total_weight_kg": None,
                        "total_cbm": None,
                        "dimensions": None,
                        "fragile": True,
                        "stackable": None,
                        "hazardous": None,
                    }
                ],
            },
        }
    )


def test_embedded_json_is_extracted():
    raw = "Model draft follows:\n```json\n" + valid_payload(
        "Move delicate optical sensors from India to Germany."
    ) + "\n```\nDone."
    payload = module._extract_json_mapping_v43(raw)
    require(payload["intent"] == "logistics", payload)
    print("PASS - JSON embedded in prose or fences is extracted safely")


def test_malformed_first_response_gets_one_repair():
    outputs = iter(
        [
            '{"normalized_text": "Move delicate optical sensors from India to Germany."',
            valid_payload("Move delicate optical sensors from India to Germany."),
        ]
    )
    calls = []

    def transport(**kwargs):
        calls.append(kwargs["prompt"])
        return next(outputs)

    result = module.interpret_with_llm(
        "move delicate optical sensors from India to Germany",
        "move delicate optical sensors from India to Germany",
        transport=transport,
    )
    require(result.used_llm, result.metadata())
    require(result.reason == "validated_llm_json_repair", result.metadata())
    require(len(calls) == 2, calls)
    print("PASS - one malformed response receives exactly one schema repair attempt")


def test_numeric_guard_still_applies_after_repair():
    outputs = iter(
        [
            "not json",
            valid_payload("Move 10 delicate optical sensors from India to Germany."),
        ]
    )

    def transport(**kwargs):
        return next(outputs)

    result = module.interpret_with_llm(
        "move delicate optical sensors from India to Germany",
        "move delicate optical sensors from India to Germany",
        transport=transport,
    )
    require(not result.used_llm, result.metadata())
    require(result.reason == "numeric_guard_rejected_rewrite", result.metadata())
    print("PASS - JSON repair cannot bypass the explicit-number safety guard")


def test_transport_joins_all_text_parts():
    original_post = module.httpx.post
    original_circuit = module._CIRCUIT_OPEN_UNTIL

    class FakeResponse:
        status_code = 200
        headers = {}

        def json(self):
            text = valid_payload("Move delicate optical sensors from India to Germany.")
            midpoint = len(text) // 2
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": text[:midpoint]},
                                {"text": text[midpoint:]},
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ]
            }

        def raise_for_status(self):
            return None

    try:
        module._CIRCUIT_OPEN_UNTIL = 0.0
        module.httpx.post = lambda *args, **kwargs: FakeResponse()
        raw = module._default_gemini_transport(
            prompt="test",
            api_key="dummy",
            model="gemini-2.5-flash",
            timeout=1.0,
        )
        parsed = json.loads(raw)
        require(parsed["intent"] == "logistics", parsed)
    finally:
        module.httpx.post = original_post
        module._CIRCUIT_OPEN_UNTIL = original_circuit

    source = Path(module.__file__).read_text(encoding="utf-8")
    require('"maxOutputTokens": 8192' in source, "expanded output budget is missing")
    print("PASS - all Gemini text parts are joined and output budget is expanded")


def main():
    previous_mode = os.environ.get("LLM_INTERPRETER_MODE")
    os.environ["LLM_INTERPRETER_MODE"] = "always"
    try:
        test_embedded_json_is_extracted()
        test_malformed_first_response_gets_one_repair()
        test_numeric_guard_still_applies_after_repair()
        test_transport_joins_all_text_parts()
    finally:
        if previous_mode is None:
            os.environ.pop("LLM_INTERPRETER_MODE", None)
        else:
            os.environ["LLM_INTERPRETER_MODE"] = previous_mode

    print("All V43 Gemini JSON resilience tests passed.")


if __name__ == "__main__":
    main()
