import json
from app.text_shipment_parser import parse_shipment_text
from app.user_agent import run_user_agent_from_text


def assert_no_bad_route(response):
    dumped = json.dumps(response, default=str)
    bad_fragments = [
        "USA Glass bottles",
        "USA Give HS code",
        "USA? Tell me compliance",
    ]
    for fragment in bad_fragments:
        assert fragment not in dumped, fragment


def test_simple_total_cargo():
    prompt = "Ship 10 pallets of ceramic tiles from India to USA using CIF. Total cargo is 10 CBM and 1200 kg."
    parsed = parse_shipment_text(prompt)
    names = [item.get("name") for item in parsed.get("items", [])]
    assert "and 1200 kg" not in names, parsed
    assert parsed.get("total_cbm") == 10.0, parsed
    assert parsed.get("total_weight_kg") == 1200.0, parsed
    assert parsed["items"][0].get("total_cbm") == 10.0, parsed
    assert parsed["items"][0].get("total_weight_kg") == 1200.0, parsed

    response = run_user_agent_from_text(prompt)
    assert_no_bad_route(response)

    dumped = json.dumps(response, default=str)
    assert "and 1200 kg" not in dumped, dumped[:4000]
    assert "1200" in dumped, dumped[:4000]


def test_route_cleanup_prompts():
    prompts = [
        "Assess trade plan for ceramic tiles from India to USA. Give HS code, duty, FTA, and export strategy.",
        "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA Glass bottles are fragile Use FOB",
        "Can I export radioactive medical equipment from India to USA? Tell me compliance, risk, logistics, and documents needed.",
    ]

    for prompt in prompts:
        response = run_user_agent_from_text(prompt)
        assert_no_bad_route(response)


def test_hazard_cost_inputs():
    prompt = "I want to ship 50 TVs and 5 electric scooters from India to USA. The TVs are fragile, scooters have batteries, use CIF, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent."
    response = run_user_agent_from_text(prompt)
    assert_no_bad_route(response)

    dumped = json.dumps(response, default=str)
    for value in ["3500", "600", "8", "6"]:
        assert value in dumped, dumped[:5000]

    text_cost_inputs = response.get("text_cost_inputs", {})
    assert text_cost_inputs.get("freight_quote_usd") == 3500.0, text_cost_inputs
    assert text_cost_inputs.get("insurance_premium_usd") == 600.0, text_cost_inputs
    assert text_cost_inputs.get("duty_rate_percent") == 8.0, text_cost_inputs
    assert text_cost_inputs.get("import_tax_rate_percent") == 6.0, text_cost_inputs


def main():
    test_simple_total_cargo()
    test_route_cleanup_prompts()
    test_hazard_cost_inputs()
    print("Backend export regression tests passed.")


if __name__ == "__main__":
    main()
