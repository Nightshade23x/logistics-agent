from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
import app.backend_service as backend_service
from api_server import app

PROMPT = (
    "Ship 10 crates from India to Port of Los Angeles. "
    "Each crate is 4 ft x 3 ft x 2 ft and weighs 220.462 lb. "
    "The crates are fragile and stackable."
)


def fail(message, payload=None):
    suffix = "" if payload is None else "\n" + repr(payload)
    raise AssertionError(message + suffix)


def find_section(payload, section_id):
    sections = payload.get("ui_sections")
    if not isinstance(sections, list):
        return None
    for section in sections:
        if isinstance(section, dict) and section.get("section_id") == section_id:
            return section
    return None


def assert_logistics_authority(payload, label):
    if payload.get("detected_intent") != "logistics":
        fail(f"{label}: detected_intent is not logistics", payload)

    agents = payload.get("agents_called") or []
    if "logistics_agent" not in agents:
        fail(f"{label}: logistics_agent is missing", agents)

    if payload.get("summary") == "User Agent could not confidently route the request.":
        fail(f"{label}: stale routing summary remains", payload)

    executive = payload.get("executive_summary") or {}
    snapshot = executive.get("shipment_snapshot") or {}
    if snapshot.get("intent") != "logistics":
        fail(f"{label}: shipment snapshot intent is stale", snapshot)
    if "logistics_agent" not in (snapshot.get("agents_called") or []):
        fail(f"{label}: snapshot agents are stale", snapshot)

    section = find_section(payload, "shipment_snapshot")
    if not isinstance(section, dict):
        fail(f"{label}: shipment snapshot UI section missing", payload)
    section_metrics = section.get("metrics") or {}
    if section_metrics.get("intent") != "logistics":
        fail(f"{label}: UI intent is stale", section)
    bullets = section.get("bullets") or []
    if not any("logistics_agent" in str(value) for value in bullets):
        fail(f"{label}: UI agents bullet is stale", bullets)

    logistics_section = find_section(payload, "logistics")
    if isinstance(logistics_section, dict) and logistics_section.get("status") == "not_applicable":
        fail(f"{label}: logistics section is still not applicable", logistics_section)

    review = payload.get("logistics_quality_review")
    if isinstance(review, dict) and not review.get("applicable"):
        fail(f"{label}: logistics review is still not applicable", review)


source = Path(backend_service.__file__).read_text(encoding="utf-8-sig", errors="replace")
if "LOGISTICS_INTENT_AUTHORITY_V33" not in source:
    fail("V33 marker is missing from backend_service.py")
print("PASS - V33 final intent wrapper is installed")

synthetic = {"detected_intent": "document", "agents_called": ["document_agent"]}
unchanged = backend_service._intent_v33_apply(synthetic, "Review this invoice.")
if unchanged != synthetic:
    fail("Non-logistics payload was changed", unchanged)
print("PASS - non-logistics payloads are not reclassified")

direct = backend_service.process_text_request(PROMPT, include_raw_response=False)
assert_logistics_authority(direct, "direct backend")
print("PASS - direct backend reports logistics intent and agent")

with TestClient(app) as client:
    response = client.post(
        "/api/request/text",
        json={"user_text": PROMPT, "include_raw_response": False},
    )
if response.status_code != 200:
    fail(f"FastAPI returned HTTP {response.status_code}", response.text)
live = response.json()
assert_logistics_authority(live, "FastAPI")
print("PASS - FastAPI reports logistics intent and agent")

metrics = live.get("logistics_metrics") or {}
if metrics.get("total_weight_kg") != 1000:
    fail("V33 disturbed the 1000 kg weight fix", metrics)
print("PASS - V33 preserves the 1000 kg weight result")
