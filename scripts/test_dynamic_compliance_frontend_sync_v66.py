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


PROMPT = (
    "Ship 20 pallets of household electrical appliances from Dubai, "
    "United Arab Emirates to Haifa, Israel using CIF. Each pallet "
    "measures 1.2 m x 1.0 m x 1.1 m and weighs 350 kg. The cargo is "
    "non-hazardous, stackable, and not fragile. No ports have been "
    "selected. Check the route, applicable trade agreement, import "
    "restrictions, compliance status, and every required or conditional "
    "document."
)


def fail(message: str, value=None) -> None:
    suffix = "" if value is None else "\n" + json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )
    raise AssertionError(message + suffix)


def lower(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    ).lower()


with TestClient(app) as client:
    response = client.post(
        "/api/request/text",
        json={
            "user_text": PROMPT,
            "include_raw_response": False,
        },
    )

if response.status_code != 200:
    fail(f"HTTP {response.status_code}", response.text[:3000])

payload = response.json()
if not isinstance(payload, dict):
    fail("Response is not an object", payload)

agreement = payload.get("trade_agreement_advice") or {}
if not agreement.get("agreement_exists_in_local_reference"):
    fail("UAE-Israel CEPA was not surfaced", agreement)

route_ids = [
    section.get("section_id")
    for section in payload.get("ui_sections") or []
    if isinstance(section, dict)
]
if "route_plan" not in route_ids:
    fail("Route plan card disappeared", route_ids)

documents = payload.get("document_requirements_advice") or {}
compliance = payload.get("trade_compliance_readiness") or {}

if documents.get("item_count") != 1:
    fail("Document item count should be one cargo line", documents)
if compliance.get("item_count") != 1:
    fail("Compliance item count should be one cargo line", compliance)

ui_compliance = next(
    (
        section
        for section in payload.get("ui_sections") or []
        if isinstance(section, dict)
        and section.get("section_id") == "compliance_documents"
    ),
    {},
)
if (ui_compliance.get("metrics") or {}).get("item_count") != 1:
    fail("Frontend compliance item count is not one", ui_compliance)

narrative = lower(
    {
        "display_answer": payload.get("display_answer"),
        "frontend_answer": payload.get("frontend_answer"),
        "final_answer": payload.get("final_answer"),
    }
)

for forbidden in (
    "treat the cargo as hazardous",
    "dangerous-goods carrier acceptance",
    "dangerous goods carrier acceptance",
    "fragile handling should be stated",
    "conditional: fragile handling",
    "shipment contains hazardous",
    "non-stackable cargo",
):
    if forbidden in narrative:
        fail(
            f"Final frontend narrative still contains: {forbidden}",
            {
                "display_answer": payload.get("display_answer"),
                "frontend_answer": payload.get("frontend_answer"),
                "final_answer": payload.get("final_answer"),
            },
        )

metadata = payload.get("request_metadata") or {}
if (
    (metadata.get("dynamic_compliance_frontend_sync_v66") or {}).get(
        "status"
    )
    != "applied"
):
    fail("V66 frontend synchronisation marker is missing", metadata)

print("PASS - UAE-Israel CEPA remains visible")
print("PASS - Indicative Route Plan remains visible")
print("PASS - document/compliance/frontend item count is one")
print("PASS - final interactive frontend answer has no stale hazardous or fragile guidance")
print("All V66 frontend synchronisation regressions passed.")
