from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

import api_server
from app.integrations.service import get_carrier_quotes, get_integration_contract, list_integrations


ROOT = Path(__file__).resolve().parents[1]
PROMPT_QUOTE = {
    "origin_country": "India",
    "destination_country": "Germany",
    "total_weight_kg": 2500,
    "total_cbm": 9.6,
    "package_count": 10,
    "currency": "USD",
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    os.environ["ENABLE_MOCK_CARRIER"] = "true"
    os.environ.pop("LOGISTICS_INTEGRATION_API_KEY", None)

    catalog = list_integrations()
    demo = next((item for item in catalog["providers"] if item["provider_id"] == "demo_carrier"), None)
    require(demo is not None, "demo provider missing")
    require(demo["live"] is False, "demo provider must never be marked live")
    require(demo["provider_type"] == "mock", "demo provider type incorrect")

    result = get_carrier_quotes(PROMPT_QUOTE)
    require(result["status"] == "ok", result)
    require(len(result["quotes"]) == 2, result)
    require(all(item["source"] == "mock_estimate" for item in result["quotes"]), result)
    require(all(item["estimated"] is True and item["live"] is False for item in result["quotes"]), result)

    contract = get_integration_contract()
    require(contract["contract_version"] == "carrier-quotes.v1", contract)
    require("bearer" in contract["supported_auth_types"], contract)
    require("provider-approved browser connector" in contract["future_extension_points"], contract)

    client = TestClient(api_server.app)
    routes = {route.path for route in api_server.app.routes}
    for path in {
        "/api/integrations",
        "/api/integrations/health",
        "/api/integrations/contract",
        "/api/integrations/quotes",
    }:
        require(path in routes, f"missing route: {path}")

    response = client.post("/api/integrations/quotes", json=PROMPT_QUOTE)
    require(response.status_code == 200, response.text)
    require(response.json()["quote_count"] == 2, response.json())

    response = client.post("/api/integrations/quotes", json={"origin_country": "India", "destination_country": "Germany"})
    require(response.status_code == 422, response.text)

    files = {
        "dashboard": ROOT / "frontend" / "src" / "pages" / "Dashboard.jsx",
        "controls": ROOT / "frontend" / "src" / "components" / "ViewControls.jsx",
        "integrations": ROOT / "frontend" / "src" / "pages" / "Integrations.jsx",
        "api": ROOT / "frontend" / "src" / "api.js",
        "app": ROOT / "frontend" / "src" / "App.jsx",
        "sidebar": ROOT / "frontend" / "src" / "components" / "Sidebar.jsx",
        "styles": ROOT / "frontend" / "src" / "styles.css",
        "guide": ROOT / "docs" / "carrier_integration_guide.md",
    }
    source = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    require("USER_FRIENDLY_VIEW_V37" in source["dashboard"], "friendly view marker missing")
    require('aria-live="polite"' in source["dashboard"], "Dashboard live region missing")
    require("ViewControls" in source["dashboard"], "Dashboard view controls missing")
    require("Simple view" in source["controls"] and "Advanced view" in source["controls"], "view modes missing")
    require("Demo estimate" in source["integrations"] and "Live API" in source["integrations"], "quote-source labels missing")
    require("integrationQuotes" in source["api"], "frontend quote API missing")
    require('path="/integrations"' in source["app"], "Integrations route missing")
    require('to: "/integrations"' in source["sidebar"], "Integrations navigation missing")
    require("INTEGRATION_UX_FOUNDATION_V37" in source["styles"], "V37 styles marker missing")
    require("CAPTCHA bypass" in source["guide"], "website connector guardrail missing")

    print("PASS - provider-neutral integration contract is available")
    print("PASS - demo quotes are clearly non-live estimates")
    print("PASS - integration endpoints validate and normalize quote requests")
    print("PASS - company API page and frontend client are wired")
    print("PASS - Simple/Advanced views, text sizing, and accessibility guidance are present")
    print("PASS - future website connector guardrails are documented")


if __name__ == "__main__":
    main()
