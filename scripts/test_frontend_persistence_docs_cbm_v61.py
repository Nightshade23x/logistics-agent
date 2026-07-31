from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from api_server import app


ROOT = Path(__file__).resolve().parents[1]


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def require(condition: bool, message: str, value=None) -> None:
    if condition:
        return
    suffix = "" if value is None else "\n" + json.dumps(value, indent=2, default=str)
    raise AssertionError(message + suffix)


def post(client: TestClient, prompt: str) -> dict:
    response = client.post(
        "/api/request/text",
        json={"user_text": prompt, "include_raw_response": False},
    )
    require(response.status_code == 200, f"HTTP {response.status_code}", response.text)
    payload = response.json()
    require(isinstance(payload, dict), "API payload must be an object", payload)
    return payload


def combined_strings(value) -> str:
    return json.dumps(value, default=str).lower()


def main() -> None:
    main_js = source("frontend/src/main.jsx")
    dashboard = source("frontend/src/pages/Dashboard.jsx")
    wizard = source("frontend/src/components/GuidedShipmentWizard.jsx")
    container = source("frontend/src/pages/ContainerPlanning.jsx")

    require("DASHBOARD_INPUT_PERSISTENCE_V61" in main_js, "startup persistence marker missing")
    require(
        'localStorage.removeItem("meridian.dashboard.text")' not in main_js,
        "main.jsx still deletes the submitted prompt on application startup",
    )

    require('const DASHBOARD_TEXT_KEY = "meridian.dashboard.text";' in dashboard, "text storage key missing")
    require(
        'const DASHBOARD_SIMPLE_INPUT_MODE_KEY = "meridian.dashboard.simpleInputMode";' in dashboard,
        "simple input-mode storage key missing",
    )
    require(
        'useState(() => loadDashboardValue(DASHBOARD_TEXT_KEY, ""))' in dashboard,
        "free-text draft is not restored from storage",
    )
    # V61_WHITESPACE_TOLERANT_STORAGE_ASSERTIONS
    require(
        re.search(
            r"localStorage\.setItem\(\s*DASHBOARD_TEXT_KEY\s*,\s*text\s*\)",
            dashboard,
        ) is not None,
        "free-text draft is not persisted",
    )
    require(
        re.search(
            r"localStorage\.setItem\(\s*DASHBOARD_SIMPLE_INPUT_MODE_KEY\s*,\s*simpleInputMode\s*\)",
            dashboard,
        ) is not None,
        "free/guided selection is not persisted",
    )
    require(
        'sessionStorage.removeItem("meridian.guidedShipmentStep.v61")' in dashboard,
        "Clear current/all does not clear the persisted guided step",
    )
    require("setText(submittedText);" in dashboard, "the exact submitted prompt is not retained")

    require(
        'const STEP_SESSION_KEY = "meridian.guidedShipmentStep.v61";' in wizard,
        "guided step storage key missing",
    )
    require("function loadStep()" in wizard, "guided step restore helper missing")
    require("useState(loadStep)" in wizard, "guided wizard does not restore the saved step")
    require(
        re.search(
            r"sessionStorage\.setItem\(\s*STEP_SESSION_KEY\s*,\s*String\(step\)\s*\)",
            wizard,
        ) is not None,
        "guided wizard step is not persisted",
    )
    require(
        "sessionStorage.removeItem(STEP_SESSION_KEY)" in wizard,
        "Start over does not clear the saved guided step",
    )

    require(
        'label={userView === "simple" ? "Total cargo space" : "Total CBM"} value={canonical.totalCbm} unit="CBM"' in container,
        "cargo-space KPI still uses m³ instead of CBM",
    )

    usa_israel = (
        "Ship 10 pallets of cotton textiles from USA to Israel using FOB. "
        "Each pallet measures 1.2 m x 1.0 m x 1.1 m and weighs 300 kg. "
        "The cargo is non-hazardous, stackable, and not fragile. "
        "No departure or arrival ports have been selected. "
        "Recommend suitable origin and destination gateways. "
        "Check whether a trade agreement applies and show the rules-of-origin and proof-of-origin document requirements."
    )
    china_brazil = (
        "Ship 30 crates of industrial pumps from China to Brazil using CIF. "
        "Each crate measures 1.1 m x 0.9 m x 0.8 m and weighs 400 kg. "
        "The cargo is non-hazardous, stackable, and not fragile. "
        "No ports have been selected. Recommend suitable gateways and an indicative route. "
        "Check whether a preferential trade agreement exists and identify the required shipment and origin documents."
    )
    fragile_stackable = (
        "Ship 5 boxes of Glasses from India to Germany using CIF. "
        "Each box is 2 x 2 x 2 m and weighs 100 kg. "
        "The cargo is fragile, stackable, and does not contain hazardous materials."
    )

    with TestClient(app) as client:
        usa = post(client, usa_israel)
        china = post(client, china_brazil)
        glasses = post(client, fragile_stackable)

    usa_docs = usa.get("document_requirements_advice") or {}
    china_docs = china.get("document_requirements_advice") or {}
    glasses_docs = glasses.get("document_requirements_advice") or {}

    require(
        any("origin invoice declaration" in str(item).lower()
            for item in usa_docs.get("conditional_documents") or []),
        "USA-Israel agreement-specific origin declaration is missing",
        usa_docs,
    )
    require(
        any("standard certificate of origin" in str(item).lower()
            for item in china_docs.get("conditional_documents") or []),
        "China-Brazil generic certificate-of-origin guidance is missing",
        china_docs,
    )
    require(
        not any("origin invoice declaration" in str(item).lower()
                for item in china_docs.get("conditional_documents") or []),
        "USA-Israel origin document leaked into China-Brazil",
        china_docs,
    )

    safe_forbidden = (
        "fragile handling",
        "non-stackable",
        "dangerous goods",
        "msds",
        "hazardous cargo",
        "possible hazardous",
    )
    for label, payload in (("USA-Israel", usa), ("China-Brazil", china)):
        relevant = {
            "documents": payload.get("document_requirements_advice"),
            "compliance": payload.get("trade_compliance_readiness"),
            "sections": [
                section
                for section in payload.get("ui_sections") or []
                if isinstance(section, dict)
                and section.get("section_id") == "compliance_documents"
            ],
        }
        rendered = combined_strings(relevant)
        for phrase in safe_forbidden:
            require(
                phrase not in rendered,
                f"{label} safe cargo still shows {phrase!r}",
                relevant,
            )

    glass_conditional = [str(item).lower() for item in glasses_docs.get("conditional_documents") or []]
    require(
        any("fragile handling" in item for item in glass_conditional),
        "genuinely fragile cargo lost its fragile handling declaration",
        glasses_docs,
    )
    require(
        not any("non-stackable" in item for item in glass_conditional),
        "stackable Glasses cargo incorrectly shows a non-stackable declaration",
        glasses_docs,
    )
    require(
        "hazardous cargo" not in combined_strings(glasses_docs),
        "explicitly non-hazardous Glasses cargo still shows a hazardous warning",
        glasses_docs,
    )

    print("PASS - free-text prompt and free/guided selection persist until explicit clear")
    print("PASS - guided draft and current wizard step persist until Start over/Clear")
    print("PASS - cargo-space KPI uses CBM")
    print("PASS - origin documents vary by route/agreement")
    print("PASS - cargo-specific documents respect fragile, stackable, and non-hazardous wording")


if __name__ == "__main__":
    main()
