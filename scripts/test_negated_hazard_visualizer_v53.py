from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["LLM_INTERPRETATION_MODE"] = "off"

from fastapi.testclient import TestClient
from api_server import app


ORDINARY_PROMPT = (
    "Ship 5 boxes of Glasses from India to Germany using CIF. "
    "Each box is 2 x 2 x 2 m and weighs 100 kg. "
    "The cargo is fragile, stackable, does not contain hazardous materials. "
    "The working budget is 20000 USD."
)

SPECIAL_PROMPT = (
    "Ship 2 crates of lithium-ion batteries from India to Germany. "
    "Each crate is 1 x 1 x 1 m and weighs 100 kg."
)


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
    payload = response.json()
    if not isinstance(payload, dict):
        fail("Expected a dictionary payload", payload)
    return payload


with TestClient(app) as client:
    ordinary = post(client, ORDINARY_PROMPT)
    special = post(client, SPECIAL_PROMPT)

metrics = ordinary.get("logistics_metrics") or {}
if abs(float(metrics.get("total_cbm") or 0) - 40.0) > 0.001:
    fail("Ordinary shipment CBM changed", metrics)
if abs(float(metrics.get("total_weight_kg") or 0) - 500.0) > 0.001:
    fail("Ordinary shipment weight changed", metrics)

visualizer = ordinary.get("logistics_visualizer") or {}
if visualizer.get("status") != "available":
    fail("Negated hazardous phrase still blocks the visualizer", visualizer)

container = visualizer.get("container") or {}
selected = str(container.get("selected_container") or "")
if selected not in {
    "40ft Standard Container",
    "40ft High Cube Container",
}:
    fail("40 CBM shipment did not receive a usable 40ft container", container)

# CONTAINER_DISPLAY_METRICS_REGRESSION_V55
display = visualizer.get("display_metrics") or {}
if abs(float(display.get("loaded_cbm") or 0) - 40.0) > 0.001:
    fail("3D display loaded CBM is incorrect", display)
if abs(float(display.get("container_cbm") or 0) - 67.7) > 0.001:
    fail("3D display container capacity is incorrect", display)
if abs(float(display.get("remaining_cbm") or 0) - 27.7) > 0.001:
    fail("3D display remaining CBM is incorrect", display)
if abs(float(display.get("utilization_percent") or 0) - 59.08) > 0.01:
    fail("3D display utilization must be 59.08%, not 0%", display)

cargo_mix = visualizer.get("cargo_mix") or []
if len(cargo_mix) != 1 or not isinstance(cargo_mix[0], dict):
    fail("Expected one visualizer cargo row", cargo_mix)

item = cargo_mix[0]
dims = item.get("dimensions_m") or {}
for key in ("length", "width", "height"):
    if abs(float(dims.get(key) or 0) - 2.0) > 0.001:
        fail("Shared trailing dimension unit was not preserved", item)
if item.get("hazardous") is not False:
    fail("Explicit non-hazardous cargo was marked hazardous", item)

fit = visualizer.get("fit_check") or {}
combined_visualizer = repr(visualizer).lower()
for stale in (
    "dangerous-goods carrier",
    "dangerous goods",
    "confirm un number",
    "battery rating",
):
    if stale in combined_visualizer:
        fail("False dangerous-goods guidance remains in the visualizer", visualizer)

special_visualizer = special.get("logistics_visualizer") or {}
special_item = special.get("authoritative_shipment_item_v49") or {}
if special_visualizer.get("status") != "review_required":
    fail("Positive lithium-battery detection was weakened", special_visualizer)
if special_item.get("hazardous") is not True:
    fail("Positive lithium-battery cargo is not marked hazardous", special_item)

source = (ROOT / "app/backend_service.py").read_text(
    encoding="utf-8-sig",
    errors="replace",
)
if "NEGATED_HAZARD_STANDARD_VISUALIZER_V53" not in source:
    fail("V53 source marker is missing")

print("PASS - negated hazardous phrase no longer triggers dangerous-goods handling")
print("PASS - shared trailing dimension unit produces 2 m x 2 m x 2 m")
print("PASS - 40 CBM / 500 kg shipment returns an available 40ft visualizer")
print("PASS - 3D display metrics report 59.08% used and 27.7 CBM remaining")
print("PASS - genuine lithium-battery cargo remains specialist review required")
