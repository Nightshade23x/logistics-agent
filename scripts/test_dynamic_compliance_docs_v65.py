from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from fastapi.testclient import TestClient
from api_server import app


def fail(message: str, value=None) -> None:
    suffix = "" if value is None else "\n" + json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )
    raise AssertionError(message + suffix)


def post(client: TestClient, prompt: str) -> dict:
    response = client.post(
        "/api/request/text",
        json={
            "user_text": prompt,
            "include_raw_response": False,
        },
    )
    if response.status_code != 200:
        fail(
            f"HTTP {response.status_code}",
            response.text[:3000],
        )
    payload = response.json()
    if not isinstance(payload, dict):
        fail("Response is not an object", payload)
    return payload


def text(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    ).lower()


def ui_compliance(payload: dict) -> dict:
    for section in payload.get("ui_sections") or []:
        if isinstance(section, dict) and section.get("section_id") in {
            "compliance_documents",
            "documents",
            "compliance",
        }:
            return section
    return {}


ordinary_prompt = (
    "Ship 20 pallets of household electrical appliances from Dubai, "
    "United Arab Emirates to Haifa, Israel using CIF. Each pallet "
    "measures 1.2 m x 1.0 m x 1.1 m and weighs 350 kg. The cargo is "
    "non-hazardous, stackable, and not fragile. No ports have been "
    "selected. Check route, trade agreement, import restrictions, "
    "compliance status, and every required or conditional document."
)

iran_prompt = (
    "Ship 10 crates of ordinary industrial machine parts from Tehran, "
    "Iran to Haifa, Israel using CIF. Each crate measures 1.0 m x "
    "0.8 m x 0.7 m and weighs 300 kg. The goods are non-hazardous "
    "and not military items. Check whether this country pair is "
    "allowed, restricted, prohibited, or subject to sanctions or "
    "import licensing. Show the exact compliance blockers, approvals, "
    "and documents required before booking."
)

dual_prompt = (
    "Ship 50 commercial drones with thermal cameras from Dubai, "
    "United Arab Emirates to Israel using CIF. The drones are intended "
    "for industrial inspection and are not weapons. Check dual-use "
    "classification, export controls, end-user documentation, import "
    "permits, carrier acceptance, and all required or conditional "
    "documents."
)

battery_prompt = (
    "Ship 4 pallets of standalone lithium-ion batteries from Shanghai, "
    "China to Hamburg, Germany using CIF. Each pallet measures 1.2 m "
    "x 1.0 m x 1.0 m and weighs 450 kg. The batteries are hazardous "
    "cargo. Check the dangerous-goods classification, packing and "
    "labelling requirements, carrier approval, insurance review, and "
    "every required or conditional document including battery test "
    "evidence."
)

radioactive_prompt = (
    "Plan a shipment of one sealed Iridium-192 industrial radiography "
    "source from France to the United States. The cargo is radioactive "
    "Class 7 material. Do not assume it is ready to ship. Identify all "
    "blockers, competent-authority permits, package certification, "
    "dangerous-goods documents, security controls, insurance review, "
    "and carrier approvals."
)


with TestClient(app) as client:
    ordinary = post(client, ordinary_prompt)
    agreement = ordinary.get("trade_agreement_advice") or {}
    if not agreement.get("agreement_exists_in_local_reference"):
        fail("UAE-Israel CEPA was not surfaced", agreement)
    if "cepa" not in text(agreement):
        fail("UAE-Israel CEPA name is missing", agreement)

    ordinary_blob = text(
        {
            "quality": ordinary.get("logistics_quality_review"),
            "insurance": ordinary.get("insurance_advice"),
            "final": ordinary.get("final_answer"),
            "ui": ordinary.get("ui_sections"),
        }
    )
    for forbidden in (
        "treat the cargo as hazardous",
        "shipment contains hazardous",
        "fragile handling",
        "non-stackable cargo",
    ):
        if forbidden in ordinary_blob:
            fail(
                f"Ordinary explicitly negated cargo still contains: {forbidden}",
                ordinary,
            )
    print("PASS - ordinary UAE-Israel cargo is not mixed up with DG/fragile/non-stackable cargo")
    print("PASS - UAE-Israel CEPA is visible in backend and UI payload")

    iran = post(client, iran_prompt)
    iran_blob = text(
        {
            "control": iran.get("country_pair_control"),
            "compliance": iran.get("trade_compliance_readiness"),
            "documents": iran.get("document_requirements_advice"),
            "ui": ui_compliance(iran),
        }
    )
    for required in (
        "blocked",
        "licence",
        "sanctions",
        "restricted-party",
        "official",
    ):
        if required not in iran_blob:
            fail(
                f"Iran-Israel control is missing keyword: {required}",
                iran,
            )
    print("PASS - Iran-Israel is blocked pending official sanctions and licensing review")

    dual = post(client, dual_prompt)
    dual_blob = text(
        {
            "controls": dual.get("special_cargo_controls"),
            "compliance": dual.get("trade_compliance_readiness"),
            "documents": dual.get("document_requirements_advice"),
            "ui": ui_compliance(dual),
        }
    )
    for required in (
        "dual-use",
        "export-control licence",
        "end-user certificate",
        "end-use statement",
        "import permit",
    ):
        if required not in dual_blob:
            fail(
                f"Dual-use response is missing: {required}",
                dual,
            )
    if (
        (dual.get("trade_compliance_readiness") or {}).get("item_count")
        or 0
    ) < 1:
        fail("Dual-use item was not retained for compliance review", dual)
    print("PASS - dual-use controls and documents are dynamic and visible to the frontend")

    battery = post(client, battery_prompt)
    battery_blob = text(
        {
            "documents": battery.get("document_requirements_advice"),
            "compliance": battery.get("trade_compliance_readiness"),
            "ui": ui_compliance(battery),
        }
    )
    for required in (
        "un38.3",
        "battery declaration",
        "dangerous goods declaration",
        "carrier dangerous-goods acceptance",
    ):
        if required not in battery_blob:
            fail(
                f"Lithium battery response is missing: {required}",
                battery,
            )
    print("PASS - lithium batteries add UN38.3 and DG documents")

    radioactive = post(client, radioactive_prompt)
    radioactive_blob = text(
        {
            "controls": radioactive.get("special_cargo_controls"),
            "compliance": radioactive.get("trade_compliance_readiness"),
            "documents": radioactive.get("document_requirements_advice"),
            "ui": ui_compliance(radioactive),
        }
    )
    for required in (
        "radioactive class 7",
        "competent-authority",
        "package design certificate",
        "transport security plan",
        "carrier acceptance",
    ):
        if required not in radioactive_blob:
            fail(
                f"Radioactive response is missing: {required}",
                radioactive,
            )
    print("PASS - radioactive Class 7 permits, package certification, security, and approvals are surfaced")

print("All V65 dynamic compliance/document regressions passed.")
