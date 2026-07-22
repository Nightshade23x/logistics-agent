import json
from app.frontend_response_cleanup import cleanup_frontend_response
from app.user_agent import run_user_agent_from_text

prompts = {
    "shopping": "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
    "simple": "Ship 10 pallets of ceramic tiles from India to USA using CIF. Total cargo is 10 CBM and 1200 kg.",
    "hazard": "I want to ship 50 TVs and 5 electric scooters from India to USA. The TVs are fragile, scooters have batteries, use CIF, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent.",
    "trader": "Assess trade plan for ceramic tiles from India to USA. Give HS code, duty, FTA, and export strategy.",
}

bad_fragments = [
    "USA Glass bottles",
    "USA Give HS code",
    "USA? Tell me compliance",
]


def walk(obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, f"{path}[{idx}]")
    else:
        yield path, obj


def assert_clean(name, payload):
    hits = []
    for path, value in walk(payload):
        if not isinstance(value, str):
            continue
        if path.endswith("request_metadata.input_source"):
            continue
        for fragment in bad_fragments:
            if fragment in value:
                hits.append((path, value))
    assert not hits, (name, hits[:20])


def main():
    results = {}

    for name, prompt in prompts.items():
        response = run_user_agent_from_text(prompt)
        response = cleanup_frontend_response(response, prompt)
        results[name] = response
        assert_clean(name, response)

    simple = results["simple"]
    assert simple["logistics_metrics"]["total_cbm"] == 10, simple["logistics_metrics"]
    assert simple["logistics_metrics"]["total_weight_kg"] == 1200, simple["logistics_metrics"]
    assert '"item_name": "and 1200 kg"' not in json.dumps(simple, default=str)

    hazard = results["hazard"]
    costs = hazard.get("text_cost_inputs", {})
    assert costs.get("freight_quote_usd") == 3500.0, costs
    assert costs.get("insurance_premium_usd") == 600.0, costs
    assert costs.get("duty_rate_percent") == 8.0, costs
    assert costs.get("import_tax_rate_percent") == 6.0, costs

    for path, value in walk(hazard):
        if isinstance(value, list) and path.endswith("missing_cost_inputs"):
            for key in ["freight_quote_usd", "insurance_premium_usd", "duty_rate_percent", "import_tax_rate_percent"]:
                assert key not in value, (path, key, value)

    print("Focused final frontend payload cleanup validation passed.")


if __name__ == "__main__":
    main()
