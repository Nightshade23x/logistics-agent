import json
from app.user_agent import run_user_agent_from_text

PROMPTS = [
    "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
    "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA Glass bottles are fragile Use FOB",
]


def walk(obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk(value, f"{path}[{index}]")
    else:
        yield path, obj


def main():
    for prompt in PROMPTS:
        response = run_user_agent_from_text(prompt)

        bad_values = []
        for path, value in walk(response):
            if isinstance(value, str) and "USA Glass bottles" in value:
                # Do not fail on the original user text if it is stored anywhere.
                if "original" not in path.lower() and "request_text" not in path.lower() and "user_text" not in path.lower():
                    bad_values.append((path, value))

        if bad_values:
            print("BAD ROUTE VALUES FOUND:")
            for path, value in bad_values[:30]:
                print(f"{path}: {value}")
            raise AssertionError("No backend report/display field should contain 'USA Glass bottles...'")

        dumped = json.dumps(response, default=str)

        if '"destination_country": "USA"' not in dumped and '"destination": "USA"' not in dumped:
            print(json.dumps(response, indent=2, default=str)[:6000])
            raise AssertionError("Expected clean destination USA somewhere in final response.")

        if "FOB" not in dumped:
            raise AssertionError("Expected incoterm FOB to be preserved.")

        agents = response.get("agents_called") or []
        if "shopping_agent" not in agents or "logistics_agent" not in agents:
            raise AssertionError(f"Expected shopping/logistics agents, got {agents}")

    print("Full pipeline route precedence regression tests passed.")


if __name__ == "__main__":
    main()
