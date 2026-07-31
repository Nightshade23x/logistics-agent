from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["LLM_INTERPRETER_MODE"] = "off"

from fastapi.testclient import TestClient
from api_server import app


def require(condition, message, value=None):
    if condition:
        return
    suffix = "" if value is None else f"\nVALUE: {value!r}"
    raise AssertionError(message + suffix)


def request(client, prompt):
    response = client.post(
        "/api/request/text",
        json={
            "user_text": prompt,
            "include_raw_response": False,
        },
    )
    require(
        response.status_code == 200,
        f"HTTP {response.status_code}",
        response.text[:2000],
    )
    payload = response.json()
    require(isinstance(payload, dict), "Payload is not an object")
    return payload


with TestClient(app) as client:
    lbs = request(
        client,
        "Ship 10 crates of ceramic tiles from India to Germany using CIF. "
        "Each crate is 1.2 m x 1.0 m x 0.8 m and weighs 250 lbs. "
        "The cargo is fragile and stackable.",
    )
    llbs = request(
        client,
        "Ship 10 crates of ceramic tiles from India to Germany using CIF. "
        "Each crate is 1.2 m x 1.0 m x 0.8 m and weighs 250 llbs. "
        "The cargo is fragile and stackable.",
    )
    litres = request(
        client,
        "Ship 10 crates of liquid product from India to Germany using CIF. "
        "Each crate has packed volume of 100 litres. "
        "Original package volume: 100 litres. "
        "The total shipment volume is 1 CBM for calculation. "
        "1 CBM of liquid product weighing 1133.980925 kg total. "
        "Each crate weighs 250 lb.",
    )


for label, payload in (("lbs", lbs), ("llbs", llbs)):
    weight = (
        (payload.get("display_measurements") or {}).get("weight")
        or {}
    )
    metrics = payload.get("logistics_metrics") or {}
    metadata = payload.get("request_metadata") or {}

    require(
        weight.get("display_unit") == "lb",
        f"{label}: final display unit should be lb",
        {
            "weight": weight,
            "metadata": metadata,
        },
    )
    require(
        abs(float(weight.get("unit_weight") or 0) - 250) < 0.001,
        f"{label}: per-package display weight should be 250 lb",
        weight,
    )
    require(
        abs(float(weight.get("total_weight") or 0) - 2500) < 0.001,
        f"{label}: total display weight should be 2500 lb",
        weight,
    )
    require(
        abs(float(metrics.get("total_weight_kg") or 0) - 1133.980925)
        < 0.1,
        f"{label}: internal kilogram total changed",
        metrics,
    )
    require(
        (metadata.get("final_display_unit_authority_v71") or {}).get(
            "weight_unit"
        )
        == "lb",
        f"{label}: final cleanup wrapper did not run",
        metadata,
    )


volume = (
    (litres.get("display_measurements") or {}).get("volume")
    or {}
)
weight = (
    (litres.get("display_measurements") or {}).get("weight")
    or {}
)
metrics = litres.get("logistics_metrics") or {}
metadata = litres.get("request_metadata") or {}

require(volume.get("display_unit") == "L", "Litres were not preserved", volume)
require(
    abs(float(volume.get("unit_volume") or 0) - 100) < 0.001,
    "Per-package volume should be 100 L",
    volume,
)
require(
    abs(float(volume.get("total_volume") or 0) - 1000) < 0.001,
    "Total display volume should be 1000 L",
    volume,
)
require(
    abs(float(metrics.get("total_cbm") or 0) - 1) < 0.001,
    "Internal volume should remain 1 CBM",
    metrics,
)
require(weight.get("display_unit") == "lb", "Weight should remain lb", weight)
require(
    (metadata.get("final_display_unit_authority_v71") or {}).get(
        "volume_unit"
    )
    == "L",
    "Final cleanup wrapper did not preserve litres",
    metadata,
)

wizard = (
    ROOT / "frontend/src/components/GuidedShipmentWizard.jsx"
).read_text(encoding="utf-8", errors="replace")
app_source = (
    ROOT / "frontend/src/App.jsx"
).read_text(encoding="utf-8", errors="replace")
sidebar = (
    ROOT / "frontend/src/components/Sidebar.jsx"
).read_text(encoding="utf-8", errors="replace")
answer_card = (
    ROOT / "frontend/src/components/AnswerCard.jsx"
).read_text(encoding="utf-8", errors="replace")

for token in (
    "customCurrency",
    "customWeightUnit",
    "customVolumeUnit",
    "customDimensionUnit",
    "litres",
):
    require(token in wizard, f"Guided form is missing {token}")

require("/process-flow" in app_source, "Process Flow route is missing")
require("/process-flow" in sidebar, "Process Flow sidebar item is missing")
require("AnswerFlow" not in answer_card, "Flowchart is still inside AnswerCard")

print("PASS - final cleanup preserves lbs and llbs as pounds")
print("PASS - internal kilograms remain unchanged")
print("PASS - final cleanup preserves litres while CBM remains internal")
print("PASS - custom units and custom currency remain present")
print("PASS - Process Flow remains on its own tab")
print("All V71 mentor-feedback smoke tests passed.")
