from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api_server import app
from app.route_trade_enrichment import _explicit_port_route


OUT = Path("test_outputs")
OUT.mkdir(parents=True, exist_ok=True)

NO_PORTS_PROMPT = (
    "Ship 10 pallets of cotton textiles from USA to Israel using FOB. "
    "Each pallet measures 1.2 m x 1.0 m x 1.1 m and weighs 300 kg. "
    "The cargo is non-hazardous, stackable, and not fragile. "
    "No departure or arrival ports have been selected. "
    "Recommend suitable origin and destination gateways and provide an indicative transport route. "
    "Check whether a trade agreement applies and show the rules-of-origin and proof-of-origin document requirements. "
    "The working budget is 25000 USD."
)

EXPLICIT_PORTS_PROMPT = (
    "Ship 10 pallets of textiles from the Port of Los Angeles, USA "
    "to the Port of Haifa, Israel using FOB. "
    "Each pallet measures 1.2 m x 1.0 m x 1.1 m and weighs 300 kg. "
    "Use the ports exactly as stated. "
    "Show the indicative route and applicable trade-agreement documentation."
)


def fail(message: str, value=None) -> None:
    suffix = "" if value is None else "\n" + json.dumps(value, indent=2, default=str)
    raise AssertionError(message + suffix)


def post(client: TestClient, prompt: str) -> dict:
    response = client.post(
        "/api/request/text",
        json={"user_text": prompt, "include_raw_response": False},
    )
    if response.status_code != 200:
        fail(f"HTTP {response.status_code}", response.text)
    payload = response.json()
    if not isinstance(payload, dict):
        fail("API payload is not an object", payload)
    return payload


def gateway_name(route: dict, key: str) -> str:
    gateway = route.get(key)
    if not isinstance(gateway, dict):
        return ""
    return str(gateway.get("name") or "").strip()


def main() -> None:
    parsed = _explicit_port_route(NO_PORTS_PROMPT)
    if parsed.get("origin_port") is not None:
        fail("Negative no-ports wording produced an origin port", parsed)
    if parsed.get("destination_port") is not None:
        fail("Negative no-ports wording produced a destination port", parsed)

    with TestClient(app) as client:
        no_ports_payload = post(client, NO_PORTS_PROMPT)
        explicit_payload = post(client, EXPLICIT_PORTS_PROMPT)

    no_ports_route = no_ports_payload.get("route_plan")
    if not isinstance(no_ports_route, dict):
        fail("No route_plan was returned for the no-ports prompt", no_ports_payload)

    origin_name = gateway_name(no_ports_route, "origin_gateway")
    destination_name = gateway_name(no_ports_route, "destination_gateway")
    selection_basis = no_ports_route.get("port_selection_basis")

    if selection_basis != "reference_gateway_selection":
        fail("No-ports prompt must use reference gateway selection", no_ports_route)

    bad_fragments = (
        "selected",
        "specified",
        "provided",
        "mentioned",
        "confirmed",
        "have been",
        "has been",
    )
    for name in (origin_name, destination_name):
        lowered = name.lower()
        if any(fragment in lowered for fragment in bad_fragments):
            fail("Placeholder prose leaked into a gateway name", no_ports_route)

    if destination_name not in {"Port of Haifa", "Port of Ashdod"}:
        fail("USA-to-Israel no-ports prompt did not choose a valid Israeli gateway", no_ports_route)

    explicit_route = explicit_payload.get("route_plan")
    if not isinstance(explicit_route, dict):
        fail("No route_plan was returned for the explicit-port prompt", explicit_payload)

    if explicit_route.get("port_selection_basis") != "user_supplied_ports":
        fail("Explicit ports were not marked as user supplied", explicit_route)

    if gateway_name(explicit_route, "origin_gateway") != "Port of Los Angeles":
        fail("Explicit origin port was not preserved", explicit_route)

    if gateway_name(explicit_route, "destination_gateway") != "Port of Haifa":
        fail("Explicit destination port was not preserved", explicit_route)

    OUT.joinpath("route_trade_v60_no_ports_selected.json").write_text(
        json.dumps(no_ports_payload, indent=2, default=str),
        encoding="utf-8",
    )
    OUT.joinpath("route_trade_v60_explicit_ports.json").write_text(
        json.dumps(explicit_payload, indent=2, default=str),
        encoding="utf-8",
    )

    print("PASS - negative no-ports wording produces no fake port")
    print(f"PASS - reference gateways selected: {origin_name} -> {destination_name}")
    print("PASS - explicit Port of Los Angeles -> Port of Haifa remains preserved")


if __name__ == "__main__":
    main()
