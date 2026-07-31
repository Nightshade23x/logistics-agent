from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api_server import app

DIRECT_PROMPT = (
    "Calculate landed cost for glass bottles from India to USA using CIF. "
    "Procurement value 15000 USD, freight quote 2200 USD, insurance premium "
    "500 USD, duty rate 6 percent, import tax 7 percent, customs brokerage "
    "300 USD, and local delivery 650 USD."
)

BASE_PROMPT = (
    "Ship 8 pallets of glass jars from India to USA. "
    "Each pallet is 1.2 m x 1.0 m x 1.5 m and weighs 180 kg. "
    "The cargo is fragile."
)

ADDITION = (
    "Use CIF. Procurement value is 15000 USD, freight quote is 2200 USD, "
    "insurance premium is 500 USD, duty rate is 6 percent, import tax is "
    "7 percent, customs brokerage is 300 USD, and local delivery is 650 USD."
)

MERGED_PROMPT = BASE_PROMPT + "\n\nAdditional information:\n" + ADDITION


def fail(message, value=None):
    suffix = "" if value is None else "\n" + repr(value)
    raise AssertionError(message + suffix)


def post(client, prompt):
    response = client.post(
        "/api/request/text",
        json={"user_text": prompt, "include_raw_response": False},
    )
    if response.status_code != 200:
        fail(f"HTTP {response.status_code}", response.text)
    return response.json()


def assert_total(payload):
    advice = payload.get("landed_cost_advice") or {}
    estimate = advice.get("estimated_landed_cost_usd")
    if estimate is None or abs(float(estimate) - 21025.34) > 0.01:
        fail("Expected landed cost 21025.34", advice)


with TestClient(app) as client:
    direct = post(client, DIRECT_PROMPT)
    merged = post(client, MERGED_PROMPT)

assert_total(direct)
direct_answer = str((direct.get("final_answer") or {}).get("answer_text") or "")
if not direct_answer.startswith("Estimated landed cost: $21,025.34 USD"):
    fail("V36 disturbed the V35 direct landed-cost answer", direct_answer)
print("PASS - direct landed-cost answer remains calculation-first")

assert_total(merged)
final_answer = merged.get("final_answer") or {}
answer = str(final_answer.get("answer_text") or "")
headline = str(final_answer.get("headline") or "")
short_answer = str(merged.get("short_answer") or "")

if not answer.startswith("Estimated landed cost: $21,025.34 USD"):
    fail("Completed missing-information answer does not lead with landed cost", answer)

for label, text in (
    ("headline", headline),
    ("answer", answer),
    ("short_answer", short_answer),
):
    if "21,025.34" not in text:
        fail(f"{label} does not surface the calculated total", text)

if "Landed cost breakdown:" not in answer:
    fail("Landed-cost breakdown is absent", answer)

for required in (
    "Procurement value: $15,000.00",
    "Freight: $2,200.00",
    "Insurance: $500.00",
    "Estimated duty (6%): $1,062.00",
    "Estimated import tax (7%): $1,313.34",
    "Customs brokerage: $300.00",
    "Local delivery: $650.00",
):
    if required not in answer:
        fail(f"Missing landed-cost line: {required}", answer)

for stale in (
    "Cost inputs still needed",
    "Confirm final supplier/cargo value before insurance and landed-cost calculation",
    "Add declared cargo value and freight/insurance/tax inputs if landed cost is needed",
):
    if stale in answer:
        fail(f"Stale completed-cost guidance remains: {stale}", answer)

metrics = merged.get("logistics_metrics") or {}
if abs(float(metrics.get("total_cbm") or 0) - 14.4) > 0.001:
    fail("CBM changed", metrics)
if abs(float(metrics.get("total_weight_kg") or 0) - 1440) > 0.001:
    fail("Weight changed", metrics)

visualizer = merged.get("logistics_visualizer") or {}
container = visualizer.get("container") or {}
if int(float(container.get("total_items") or 0)) != 8:
    fail("Quantity changed", container)

request_metadata = merged.get("request_metadata") or {}
input_source = str(request_metadata.get("input_source") or "")
if "Additional information:" not in input_source or "Procurement value is 15000 USD" not in input_source:
    fail("Merged request metadata was lost", request_metadata)

source = (ROOT / "app/backend_service.py").read_text(
    encoding="utf-8-sig",
    errors="replace",
)
if "COMPLETED_LANDED_COST_ANSWER_SYNC_V36" not in source:
    fail("V36 marker is missing")

print("PASS - completed missing-information answer leads with $21,025.34")
print("PASS - landed-cost breakdown is included in the answer")
print("PASS - stale missing-cost guidance is removed")
print("PASS - shipment CBM, weight, quantity, and merged request are preserved")
