from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api_server import app
from app.route_trade_enrichment import enrich_route_trade_payload


OUT = ROOT / "test_outputs"
OUT.mkdir(parents=True, exist_ok=True)


def fail(message, value=None):
    suffix = "" if value is None else "\n" + json.dumps(value, indent=2, default=str)
    raise AssertionError(message + suffix)


def post(client, prompt):
    response = client.post(
        "/api/request/text",
        json={"user_text": prompt, "include_raw_response": False},
    )
    if response.status_code != 200:
        fail(f"HTTP {response.status_code}", response.text)
    return response.json()


USA_ISRAEL = (
    "Ship 100 packages of bicycles from USA to Israel using FOB. "
    "Each package is 4 x 4 x 1 m and weighs 1000 kg. "
    "The cargo is not fragile, stackable, and does not contain hazardous materials. "
    "The working budget is 10000 USD. Suggest suitable departure and arrival ports, "
    "an indicative route, route cautions, and any applicable trade agreement or preferential-origin documents."
)

INDIA_GERMANY = (
    "Ship 5 boxes of glasses from India to Germany using CIF. "
    "Each box is 2 x 2 x 2 m and weighs 100 kg. "
    "The cargo is fragile, stackable, and non-hazardous."
)

CHINA_BRAZIL = (
    "Ship 12 pallets of machinery parts from China to Brazil using CFR. "
    "Each pallet is 1.2 x 1.0 x 1.1 m and weighs 600 kg."
)

ZAMBIA_FINLAND = (
    "Ship 8 crates of copper components from Zambia to Finland using DAP. "
    "Each crate is 1.1 x 0.9 x 0.8 m and weighs 700 kg."
)

EXPLICIT_PORTS = (
    "Ship 10 pallets of textiles from Port of Los Angeles, USA to Port of Haifa, Israel "
    "using FOB. Each pallet is 1.2 x 1.0 x 1.1 m and weighs 300 kg. "
    "Use the ports exactly as stated and report any applicable trade-agreement or origin documents."
)


with TestClient(app) as client:
    usa = post(client, USA_ISRAEL)
    route = usa.get("route_plan") or {}
    agreement = usa.get("trade_agreement_advice") or {}

    if route.get("origin_country") != "USA" or route.get("destination_country") != "Israel":
        fail("USA-Israel countries were not preserved", route)
    if not (route.get("origin_gateway") or {}).get("name"):
        fail("USA-Israel origin gateway missing", route)
    if not (route.get("destination_gateway") or {}).get("name"):
        fail("USA-Israel destination gateway missing", route)
    if route.get("live_advisory_status") != "not_connected":
        fail("Static route must not pretend live advisories were checked", route)
    if not agreement.get("agreement_exists_in_local_reference"):
        fail("U.S.-Israel FTA was not found in local Trader data", agreement)
    if "israel" not in str(agreement.get("agreement_name") or "").lower():
        fail("U.S.-Israel agreement name is missing", agreement)
    documents = agreement.get("proof_of_origin_documents") or []
    if not any("origin invoice declaration" in str(item).lower() for item in documents):
        fail("U.S. Origin Invoice Declaration was not surfaced", agreement)

    section_ids = [
        section.get("section_id")
        for section in usa.get("ui_sections") or []
        if isinstance(section, dict)
    ]
    if "route_plan" not in section_ids:
        fail("Route plan card did not reach ui_sections", section_ids)
    compliance = next(
        (
            section
            for section in usa.get("ui_sections") or []
            if isinstance(section, dict) and section.get("section_id") == "compliance_documents"
        ),
        {},
    )
    compliance_metrics = compliance.get("metrics") or {}
    if "Israel" not in str(compliance_metrics.get("agreement_name") or ""):
        fail("Agreement did not reach Compliance & Documents metrics", compliance)

    OUT.joinpath("route_trade_v59_usa_israel.json").write_text(
        json.dumps(usa, indent=2, default=str),
        encoding="utf-8",
    )
    print("PASS - USA to Israel receives ports, an indicative corridor, FTA data and origin documents")

    india = post(client, INDIA_GERMANY)
    if not (india.get("route_plan") or {}).get("indicative_corridor"):
        fail("India-Germany route missing", india.get("route_plan"))
    if "trade_agreement_advice" not in india:
        fail("India-Germany agreement check missing")
    print("PASS - India to Germany uses the generic route and agreement pipeline")

    china = post(client, CHINA_BRAZIL)
    if not (china.get("route_plan") or {}).get("indicative_corridor"):
        fail("China-Brazil route missing", china.get("route_plan"))
    print("PASS - China to Brazil uses the generic route pipeline")

    zambia = post(client, ZAMBIA_FINLAND)
    zambia_route = zambia.get("route_plan") or {}
    if not zambia_route.get("inland_precarriage_required"):
        fail("Zambia must be treated as a landlocked origin", zambia_route)
    origin_gateway = zambia_route.get("origin_gateway") or {}
    if origin_gateway.get("gateway_country") == "Zambia":
        fail("Zambia gateway must be a regional seaport", origin_gateway)
    print("PASS - Zambia to Finland includes inland pre-carriage to a regional gateway")

    explicit = post(client, EXPLICIT_PORTS)
    explicit_route = explicit.get("route_plan") or {}
    if "Los Angeles" not in str((explicit_route.get("origin_gateway") or {}).get("name")):
        fail("Explicit Los Angeles port was overwritten", explicit_route)
    if "Haifa" not in str((explicit_route.get("destination_gateway") or {}).get("name")):
        fail("Explicit Haifa port was overwritten", explicit_route)
    if explicit_route.get("port_selection_basis") != "user_supplied_ports":
        fail("Explicit-port route basis is wrong", explicit_route)
    if explicit.get("destination_country") != "Israel":
        fail("Explicit port prompt did not recover Israel as the destination country", explicit)
    print("PASS - explicitly supplied ports are preserved exactly")

fallback = {
    "origin_country": "Nepal",
    "destination_country": "Iceland",
    "ui_sections": [],
    "request_metadata": {"input_source": "Ship cargo from Nepal to Iceland."},
}
enrich_route_trade_payload(fallback, "Ship cargo from Nepal to Iceland.")
fallback_route = fallback.get("route_plan") or {}
if not fallback_route.get("indicative_corridor"):
    fail("Unknown-reference country pair did not receive a safe fallback route", fallback_route)
if fallback_route.get("port_selection_basis") != "carrier_gateway_confirmation_required":
    fail("Unknown-reference countries must request carrier gateway confirmation", fallback_route)
print("PASS - countries outside the gateway table degrade safely instead of hardcoding a pair")

print("All V59 route-plan and trade-agreement frontend integration tests passed.")
