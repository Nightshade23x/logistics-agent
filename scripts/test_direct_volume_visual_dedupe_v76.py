from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VISUALIZER = ROOT / "frontend/src/components/Container3DVisualizer.jsx"

source = VISUALIZER.read_text(
    encoding="utf-8",
    errors="replace",
)

required = (
    "DIRECT_VOLUME_VISUAL_DEDUPE_V76",
    "syntheticCalculationItemV76",
    'label.includes("for calculation")',
    "cleanedCargoV76",
    "cleanedBoxesV76",
    "cleanedSequenceV76",
    "cargo_mix: cleanedCargoV76",
    "boxes: cleanedBoxesV76",
    "loading_sequence: cleanedSequenceV76",
    "visual_units: cleanedBoxesV76.length",
)

for token in required:
    assert token in source, f"Missing V76 visual dedupe token: {token}"

os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)
os.environ["LLM_INTERPRETER_MODE"] = "off"
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from fastapi.testclient import TestClient
from api_server import app

prompt = (
    "Ship 1 crate of ceramic tiles from India to Germany using CIF. "
    "Each crate has packed volume of 200 litres. "
    "Original package volume: 200 litres. "
    "The total shipment volume is 0.2 CBM for calculation. "
    "0.2 CBM of ceramic tiles weighing 250 kg total. "
    "Each crate weighs 250 kg. "
    "The cargo is fragile and stackable."
)

with TestClient(app) as client:
    response = client.post(
        "/api/request/text",
        json={
            "user_text": prompt,
            "include_raw_response": False,
        },
    )

assert response.status_code == 200, response.text[:2000]
payload = response.json()

visualizer = payload.get("logistics_visualizer") or {}
cargo_mix = visualizer.get("cargo_mix") or []
container = visualizer.get("container") or {}

assert len(cargo_mix) == 1, cargo_mix
assert float(container.get("total_items") or 0) == 1, container
assert abs(float(container.get("total_cbm") or 0) - 0.2) < 0.001, container

print("PASS - backend returns one canonical cargo item")
print("PASS - frontend filters calculation-only cargo, boxes and sequence steps")
print("PASS - visual unit count uses the filtered box list")
print("All V76 direct-volume visual dedupe checks passed.")
