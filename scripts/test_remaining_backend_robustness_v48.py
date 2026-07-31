from __future__ import annotations

import math
import os
from typing import Any

for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "TRADE_ORCHESTRATOR_BASE_URL"):
    os.environ.pop(key, None)
os.environ["LLM_INTERPRETER_MODE"] = "off"
os.environ["LOGISTICS_AGENT_DISABLE_LOCAL_SECRETS"] = "1"
os.environ["USE_TRAINED_ROUTER"] = "0"

from app.agent_router import detect_text_intent
from app.backend_service import process_text_request


def require(condition: bool, message: Any) -> None:
    if not condition:
        raise AssertionError(message)


def close(value: Any, expected: float, tolerance: float = 1e-6) -> bool:
    try:
        return math.isclose(float(value), expected, rel_tol=0.0, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def run(prompt: str) -> dict[str, Any]:
    try:
        return process_text_request(prompt, include_raw_response=False)
    except TypeError:
        return process_text_request(prompt)


def nested_values(value: Any, key: str) -> list[Any]:
    results: list[Any] = []
    if isinstance(value, dict):
        for current_key, child in value.items():
            if current_key == key:
                results.append(child)
            results.extend(nested_values(child, key))
    elif isinstance(value, list):
        for child in value:
            results.extend(nested_values(child, key))
    return results


def metric(payload: dict[str, Any], key: str) -> Any:
    metrics = payload.get("logistics_metrics")
    return metrics.get(key) if isinstance(metrics, dict) else None


def visible_text(payload: dict[str, Any]) -> str:
    values = [payload.get("short_answer"), payload.get("display_answer"), payload.get("frontend_answer")]
    final_answer = payload.get("final_answer")
    if isinstance(final_answer, dict):
        values.append(final_answer.get("answer_text"))
    return "\n".join(str(value or "") for value in values)


def test_radioactive_shipping_guardrail() -> None:
    prompt = (
        "I need to ship a radioactive medical source from South Africa to Kenya. "
        "Package dimensions, isotope, activity and UN number are not yet confirmed."
    )
    route = detect_text_intent(prompt)
    require(route.get("detected_intent") == "logistics", route)

    payload = run(prompt)
    agents = payload.get("agents_called") or []
    require(payload.get("detected_intent") == "logistics", payload)
    require("shopping_agent" not in agents, agents)
    require("compliance_agent" in agents, agents)
    require("document_ai_agent" in agents, agents)
    missing = payload.get("missing_information") or []
    text = " ".join(str(item).lower() for item in missing)
    for token in ("dimensions", "weight", "isotope", "activity", "un number"):
        require(token in text, (token, missing))
    print("PASS - radioactive shipment remains logistics and exposes regulatory missing information")


def test_landed_cost_physical_facts() -> None:
    prompt = (
        "Calculate landed cost for 10 crates of tiles from India to USA. "
        "Each crate is 1 m x 1 m x 1 m and 100 kg. Goods value $15000, freight $3000, "
        "insurance $300, duty 5%, import tax 10%, brokerage $250, local delivery $400."
    )
    payload = run(prompt)
    require(close(metric(payload, "total_cbm"), 10.0), payload)
    require(close(metric(payload, "total_weight_kg"), 1000.0), payload)
    agents = payload.get("agents_called") or []
    require("logistics_agent" in agents and "finance_agent" in agents, agents)
    require("total weight: not confirmed" not in visible_text(payload).lower(), visible_text(payload))

    metadata = payload.get("request_metadata") or {}
    require(metadata.get("original_input_source") == prompt, metadata)
    normalization = payload.get("request_normalization_v48") or {}
    require(normalization.get("reason") == "landed_cost_physical_prefix_normalized", normalization)

    cost_values = nested_values(payload, "procurement_value_usd")
    require(any(close(value, 15000.0) for value in cost_values), cost_values)
    landed = payload.get("landed_cost_advice") or {}
    missing_costs = landed.get("missing_cost_inputs") or []
    require("procurement_value_usd" not in missing_costs, landed)
    print("PASS - landed-cost language preserves explicit cargo facts and goods value")


def test_special_cargo_weight_and_handling() -> None:
    fragile = run(
        "Ship 20 pallets of fragile glass bottles from India to USA. "
        "Each pallet is 1.2 m x 1 m x 1.4 m, 600 kg, and must not be stacked."
    )
    require(close(metric(fragile, "total_cbm"), 33.6), fragile)
    require(close(metric(fragile, "total_weight_kg"), 12000.0), fragile)
    require(False in nested_values(fragile, "stackable"), fragile)

    lithium = run(
        "Ship 50 electric scooters with lithium batteries from China to Germany. "
        "Each scooter is 1.8 m x 0.7 m x 1.2 m and 120 kg. "
        "UN number and battery Wh rating are unknown."
    )
    require(close(metric(lithium, "total_cbm"), 75.6), lithium)
    require(close(metric(lithium, "total_weight_kg"), 6000.0), lithium)
    agents = lithium.get("agents_called") or []
    require("logistics_agent" in agents, agents)
    require("compliance_agent" in agents and "document_ai_agent" in agents, agents)
    missing = " ".join(str(item).lower() for item in (lithium.get("missing_information") or []))
    require("un number" in missing and "watt-hour" in missing, missing)
    print("PASS - special cargo keeps explicit weight, handling, compliance, and document routing")


def test_booking_route_date_separation() -> None:
    payload = run("Book a 40ft high cube container from Mumbai to Hamburg next Friday.")
    require(str(payload.get("origin")).lower() == "mumbai", payload)
    require(str(payload.get("destination")).lower() == "hamburg", payload)
    require(str(payload.get("requested_date_text")).lower() == "next friday", payload)
    bad = [
        str(value).lower()
        for value in nested_values(payload, "destination") + nested_values(payload, "destination_country")
        if value and "next friday" in str(value).lower()
    ]
    require(not bad, bad)
    booking = payload.get("booking_request") or {}
    require(str(booking.get("destination")).lower() == "hamburg", booking)
    require(str(booking.get("requested_date_text")).lower() == "next friday", booking)
    print("PASS - booking destination and requested date are stored separately")


def test_missing_information_observability() -> None:
    payload = run("Ship ceramic tiles from India to Germany. Quantity, dimensions and weight are not confirmed.")
    missing = payload.get("missing_information")
    require(isinstance(missing, list) and missing, payload)
    text = " ".join(str(item).lower() for item in missing)
    for token in ("quantity", "dimensions", "weight"):
        require(token in text, (token, missing))
    require(payload.get("missing_information_count") == len(missing), payload)
    print("PASS - incomplete shipment responses expose concrete missing fields")


def test_document_agent_canonical_name() -> None:
    payload = run("Check this commercial invoice and packing list for missing shipment information.")
    agents = payload.get("agents_called") or []
    require(payload.get("detected_intent") == "document", payload)
    require("document_ai_agent" in agents, agents)
    require("document_agent" not in agents, agents)
    require(not nested_values(payload, "document_agent"), payload)
    print("PASS - document_ai_agent is the single canonical public agent name")


def test_existing_routing_stays_intact() -> None:
    shopping = detect_text_intent("Find suppliers for 50 televisions and compare price and quality.")
    require(shopping.get("detected_intent") == "shopping", shopping)

    established_procurement_prompt = "I need 50 TVs from India to USA under FOB Mumbai terms."
    procurement_route = detect_text_intent(established_procurement_prompt)
    require(procurement_route.get("detected_intent") == "shopping", procurement_route)
    procurement_payload = run(established_procurement_prompt)
    require(procurement_payload.get("detected_intent") == "shopping", procurement_payload)
    require("shopping_agent" in (procurement_payload.get("agents_called") or []), procurement_payload)

    logistics = detect_text_intent("Ship ceramic tiles from India to Germany.")
    require(logistics.get("detected_intent") == "logistics", logistics)
    print("PASS - shipping guardrail preserves supplier and quantity/origin/destination shopping requests")


def main() -> None:
    test_radioactive_shipping_guardrail()
    test_landed_cost_physical_facts()
    test_special_cargo_weight_and_handling()
    test_booking_route_date_separation()
    test_missing_information_observability()
    test_document_agent_canonical_name()
    test_existing_routing_stays_intact()
    print("All V48 remaining-backend robustness tests passed.")


if __name__ == "__main__":
    main()
