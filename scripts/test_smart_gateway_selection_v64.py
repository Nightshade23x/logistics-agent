from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.route_trade_enrichment import (
    _explicit_port_route,
    enrich_route_trade_payload,
)


def fail(message: str, value=None) -> None:
    suffix = "" if value is None else "\n" + json.dumps(value, indent=2, default=str)
    raise AssertionError(message + suffix)


def route(origin: str, destination: str, prompt: str) -> dict:
    payload = {
        "origin_country": origin,
        "destination_country": destination,
        "ui_sections": [],
        "request_metadata": {"input_source": prompt},
    }
    enrich_route_trade_payload(payload, prompt)
    return payload.get("route_plan") or {}


india_germany = route(
    "India",
    "Germany",
    "Ship cargo from India to Germany using CIF. No ports have been selected.",
)
india_origin = (india_germany.get("origin_gateway") or {}).get("name")
if india_origin != "Jawaharlal Nehru Port (Nhava Sheva)":
    fail("India-Europe country-level routing should use the west-coast reference gateway", india_germany)
if "Chennai" in str(india_origin):
    fail("India-Europe route incorrectly selected Chennai", india_germany)
if "Arabian Sea" not in str(india_germany.get("indicative_corridor") or ""):
    fail("India-Europe corridor should depart through the Arabian Sea", india_germany)
print("PASS - India to Europe selects Jawaharlal Nehru Port rather than Chennai")

india_singapore = route(
    "India",
    "Singapore",
    "Ship cargo from India to Singapore. No ports have been selected.",
)
if (india_singapore.get("origin_gateway") or {}).get("name") != "Chennai Port":
    fail("India to Southeast Asia should use the east-coast reference gateway", india_singapore)
print("PASS - the same selector chooses Chennai Port for an eastbound trade lane")

mumbai_prompt = (
    "Ship cargo from Mumbai, India to Hamburg, Germany using CIF. "
    "No ports have been selected."
)
mumbai_payload = {
    "ui_sections": [],
    "request_metadata": {"input_source": mumbai_prompt},
}
enrich_route_trade_payload(mumbai_payload, mumbai_prompt)
mumbai_route = mumbai_payload.get("route_plan") or {}
if (mumbai_route.get("origin_gateway") or {}).get("name") != "Jawaharlal Nehru Port (Nhava Sheva)":
    fail("Mumbai location hint did not select the matching service-area gateway", mumbai_route)
if (mumbai_route.get("destination_gateway") or {}).get("name") != "Port of Hamburg":
    fail("Hamburg location hint did not select Hamburg", mumbai_route)
if mumbai_route.get("port_selection_basis") != "location_and_reference_gateway_selection":
    fail("Location-based selection basis was not exposed", mumbai_route)
if (mumbai_route.get("origin_gateway") or {}).get("user_supplied"):
    fail("A city-country pair must not be mislabelled as a user-supplied port", mumbai_route)
print("PASS - city hints influence gateway choice without being mistaken for ports")

explicit_prompt = (
    "Ship cargo from Port of Chennai, India to Port of Hamburg, Germany using CIF."
)
explicit_payload = {
    "ui_sections": [],
    "request_metadata": {"input_source": explicit_prompt},
}
enrich_route_trade_payload(explicit_payload, explicit_prompt)
explicit_route = explicit_payload.get("route_plan") or {}
if (explicit_route.get("origin_gateway") or {}).get("name") != "Chennai Port":
    fail("Explicit Chennai port did not resolve to its canonical reference name", explicit_route)
if explicit_route.get("port_selection_basis") != "user_supplied_ports":
    fail("Explicit ports were not preserved as user supplied", explicit_route)
print("PASS - explicit ports remain authoritative and use canonical reference names")

custom_prompt = (
    "Ship cargo from Port of Custom Export Terminal, India "
    "to Port of Hamburg, Germany using CIF."
)
custom_payload = {
    "ui_sections": [],
    "request_metadata": {"input_source": custom_prompt},
}
enrich_route_trade_payload(custom_payload, custom_prompt)
custom_route = custom_payload.get("route_plan") or {}
custom_name = (custom_route.get("origin_gateway") or {}).get("name")
if custom_name != "Custom Export Terminal":
    fail("Unmatched explicit terminal name was altered or given a fake prefix", custom_route)
print("PASS - unmatched explicit terminal names are preserved without invented prefixes")

negative = _explicit_port_route(
    "Ship cargo from India to Germany. No departure or arrival ports have been selected."
)
if negative.get("origin_port") is not None or negative.get("destination_port") is not None:
    fail("Negative port wording was parsed as a port", negative)
print("PASS - V60 negative-port protection remains intact")

print("All V64 smart gateway-selection regressions passed.")
