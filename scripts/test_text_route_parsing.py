from app.text_shipment_parser import parse_shipment_text
from app.user_agent import _extract_route_from_text


PROMPTS = [
    (
        "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA Glass bottles are fragile Use FOB",
        "India",
        "USA",
        "FOB",
    ),
    (
        "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
        "India",
        "USA",
        "FOB",
    ),
    (
        "I want to ship 50 TVs and 5 electric scooters from India to USA. The TVs are fragile, scooters have batteries, use CIF, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent.",
        "India",
        "USA",
        "CIF",
    ),
]


def main() -> None:
    for prompt, expected_origin, expected_destination, expected_incoterm in PROMPTS:
        parsed = parse_shipment_text(prompt)
        route = _extract_route_from_text(prompt)

        assert parsed.get("origin_country") == expected_origin, parsed
        assert parsed.get("destination_country") == expected_destination, parsed
        assert parsed.get("incoterm") == expected_incoterm, parsed

        assert route.get("country_from") == expected_origin, route
        assert route.get("country_to") == expected_destination, route

        assert "Glass bottles" not in str(parsed.get("destination_country")), parsed
        assert "Use FOB" not in str(parsed.get("destination_country")), parsed

    print("Text route parsing regression tests passed.")


if __name__ == "__main__":
    main()
