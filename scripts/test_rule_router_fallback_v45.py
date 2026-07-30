from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
os.environ["USE_TRAINED_ROUTER"] = "0"
os.environ["LLM_INTERPRETER_MODE"] = "off"

from app import agent_router
from app.backend_service import process_text_request
from app.user_agent import _route_text_request, run_user_agent_from_text


LOGISTICS_PROMPTS = [
    "Ship 10 crates of ceramic tiles from India to Germany. Each crate measures 1 m x 1 m x 1 m and weighs 100 kg.",
    "Ship 10 crates of ceramic tiles from India to Germany. Each crate weighs 100 kg. Dimensions are not confirmed.",
    "Ship 10 crates of ceramic tiles from India to Germany. Each crate measures 1 m x 1 m x 1 m. Weight is not confirmed.",
    "Ship ceramic tiles from India to Germany. Quantity, dimensions and weight are not confirmed.",
    "Need help sending 8 pallets of glass jars from India to France. I do not know the dimensions yet.",
    "Ship 10 crates of ceramic tiles from India to Germany, each weighing 100 kg. Correction: the quantity is 12, not 10.",
    "Ship 8 pallets of glass jars from India to Germany. The final destination is France.",
]

COMPLETE = LOGISTICS_PROMPTS[0]
MISSING_DIMENSIONS = LOGISTICS_PROMPTS[1]
MISSING_WEIGHT = LOGISTICS_PROMPTS[2]
MISSING_ALL = LOGISTICS_PROMPTS[3]
CORRECTION = LOGISTICS_PROMPTS[5]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def metrics(payload):
    value = payload.get("logistics_metrics")
    return value if isinstance(value, dict) else {}


def close(value, expected, tolerance=0.0001):
    if value is None:
        return False
    return abs(float(value) - float(expected)) <= tolerance


def assert_logistics_intent(payload, label):
    require(
        payload.get("detected_intent") == "logistics",
        (label, payload.get("detected_intent"), payload),
    )


def assert_agent_called(payload, label):
    agents = payload.get("agents_called") or []
    require("logistics_agent" in agents, (label, agents, payload))


def test_rule_router_uses_richer_fallback_only_when_needed():
    for prompt in LOGISTICS_PROMPTS:
        routed = agent_router.detect_text_intent(prompt)
        require(routed.get("detected_intent") == "logistics", (prompt, routed))
        require((routed.get("scores") or {}).get("logistics", 0) >= 1, (prompt, routed))

    shopping = agent_router.detect_text_intent("I need 50 TVs from suppliers in India.")
    require(shopping.get("detected_intent") == "shopping", shopping)
    require((shopping.get("scores") or {}).get("shopping", 0) >= 1, shopping)

    document = agent_router.detect_text_intent("Review this commercial invoice and packing list.")
    require(document.get("detected_intent") == "document", document)
    require((document.get("scores") or {}).get("document", 0) >= 1, document)

    print("PASS - zero-score rule routing falls back to the richer deterministic classifier")


def test_user_agent_route_preserves_optional_trained_router_boundary():
    require(os.environ.get("USE_TRAINED_ROUTER") == "0", os.environ.get("USE_TRAINED_ROUTER"))
    for prompt in LOGISTICS_PROMPTS:
        routed = _route_text_request(prompt)
        require(routed.get("source") == "text", (prompt, routed))
        require(routed.get("detected_intent") == "logistics", (prompt, routed))
        require(routed.get("trained_router_decision") is None, (prompt, routed))

    source = Path(agent_router.__file__).read_text(encoding="utf-8-sig", errors="replace")
    require("RULE_ROUTER_FALLBACK_V45" in source, "V45 router marker missing")
    backend_source = (ROOT_DIR / "app" / "backend_service.py").read_text(encoding="utf-8-sig", errors="replace")
    require("CORRECTION_VOLUME_AUTHORITY_V45" in backend_source, "V45 correction-volume marker missing")
    print("PASS - trained LoRA routing remains optional and untouched when disabled")


def test_parseable_shipments_call_logistics_and_keep_authoritative_backend_totals():
    expected = {
        COMPLETE: (10.0, 1000.0),
        MISSING_DIMENSIONS: (None, 1000.0),
        MISSING_WEIGHT: (10.0, None),
        CORRECTION: (None, 1200.0),
    }

    for prompt, (expected_cbm, expected_weight) in expected.items():
        direct = run_user_agent_from_text(prompt)
        assert_logistics_intent(direct, "user_agent: " + prompt)
        assert_agent_called(direct, "user_agent: " + prompt)

        backend = process_text_request(prompt, include_raw_response=False)
        assert_logistics_intent(backend, "backend: " + prompt)
        assert_agent_called(backend, "backend: " + prompt)

        actual = metrics(backend)
        if expected_cbm is None:
            require(actual.get("total_cbm") is None, (prompt, actual))
        else:
            require(close(actual.get("total_cbm"), expected_cbm), (prompt, actual))

        if expected_weight is None:
            require(actual.get("total_weight_kg") is None, (prompt, actual))
        else:
            require(close(actual.get("total_weight_kg"), expected_weight), (prompt, actual))

        if prompt == CORRECTION:
            validation = backend.get("input_validation_v44") or {}
            facts = validation.get("authoritative_facts") or {}
            require(facts.get("correction_without_dimensions") is True, facts)
            require(any("corrected quantity" in str(value).lower() and "volume" in str(value).lower() for value in validation.get("warnings", [])), validation)

    print("PASS - parseable shipments call Logistics Agent and final authority blocks correction-only CBM estimates")


def test_unparseable_shipment_is_logistics_clarification_without_fake_agent_execution():
    direct = run_user_agent_from_text(MISSING_ALL)
    assert_logistics_intent(direct, "user_agent missing-all")
    require((direct.get("agents_called") or []) == [], direct)
    require(direct.get("status") == "needs_more_information", direct)
    require(bool(direct.get("missing_information")), direct)
    require(direct.get("specialist_response") is None, direct)

    backend = process_text_request(MISSING_ALL, include_raw_response=False)
    assert_logistics_intent(backend, "backend missing-all")
    require((backend.get("agents_called") or []) == [], backend)
    require(backend.get("status") == "needs_more_information", backend)
    require(metrics(backend).get("total_cbm") is None, metrics(backend))
    require(metrics(backend).get("total_weight_kg") is None, metrics(backend))

    print("PASS - unparseable shipment keeps logistics intent and asks questions before agent execution")


def test_remaining_incomplete_and_conflicting_prompts_keep_logistics_intent():
    for prompt in (LOGISTICS_PROMPTS[4], LOGISTICS_PROMPTS[6]):
        direct = run_user_agent_from_text(prompt)
        assert_logistics_intent(direct, "user_agent: " + prompt)

        backend = process_text_request(prompt, include_raw_response=False)
        assert_logistics_intent(backend, "backend: " + prompt)
        require(
            backend.get("status") in {
                "needs_more_information",
                "partial_plan_needs_more_information",
                "review_required",
            },
            (prompt, backend.get("status"), backend),
        )

    print("PASS - informal and conflicting shipment prompts retain logistics intent")


def test_special_routes_and_other_intents_remain_unchanged():
    booking = run_user_agent_from_text(
        "I need to send fragile optical sensors from India to Germany. What details must I confirm before booking?"
    )
    require(booking.get("detected_intent") == "booking_information", booking)

    shopping = run_user_agent_from_text("I need 50 TVs from suppliers in India.")
    require(shopping.get("detected_intent") == "shopping", shopping)
    require("shopping_agent" in (shopping.get("agents_called") or []), shopping)

    document = agent_router.detect_text_intent("Review this commercial invoice and packing list.")
    require(document.get("detected_intent") == "document", document)

    trader = _route_text_request("What HS code and import duty apply to ceramic tiles shipped to Germany?")
    require(trader.get("detected_intent") == "trader", trader)

    print("PASS - booking, shopping, document and trader routing remain unchanged")


def main():
    test_rule_router_uses_richer_fallback_only_when_needed()
    test_user_agent_route_preserves_optional_trained_router_boundary()
    test_parseable_shipments_call_logistics_and_keep_authoritative_backend_totals()
    test_unparseable_shipment_is_logistics_clarification_without_fake_agent_execution()
    test_remaining_incomplete_and_conflicting_prompts_keep_logistics_intent()
    test_special_routes_and_other_intents_remain_unchanged()
    print("All V45 rule-router fallback tests passed.")


if __name__ == "__main__":
    main()
