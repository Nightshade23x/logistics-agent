from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import json
from fastapi.testclient import TestClient

from api_server import app
from app.text_shipment_parser import parse_shipment_text

PROMPT = "20ft container of hazardous chemicals, destination Germany"

parsed = parse_shipment_text(PROMPT)
assert parsed.get("items"), parsed
assert parsed["items"][0].get("item_name") == "hazardous chemicals", parsed["items"]
assert parsed["items"][0].get("total_weight_kg") == 1000, parsed["items"][0]
assert parsed.get("destination") == "Germany" or parsed.get("destination_country") == "Germany", parsed

client = TestClient(app)
response = client.post(
    "/api/request/text",
    json={"user_text": PROMPT, "include_raw_response": True},
)
assert response.status_code == 200, response.text[:2000]

payload = response.json()
dumped = json.dumps(payload, default=str).lower()

agents = payload.get("agents_called", [])
assert "logistics_agent" in agents, payload
assert payload.get("detected_intent") == "logistics", payload.get("detected_intent")
assert "hazardous chemicals" in dumped, dumped[:3000]
assert "germany" in dumped, dumped[:3000]
assert "structured_logistics_json" not in dumped, dumped[:3000]

visualizer = payload.get("logistics_visualizer", {})
assert visualizer.get("status") == "available", visualizer

cargo_mix = visualizer.get("cargo_mix", [])
assert cargo_mix, visualizer
assert cargo_mix[0].get("item_name") == "hazardous chemicals", cargo_mix
assert cargo_mix[0].get("total_weight_kg", 0) > 0, cargo_mix

metrics = payload.get("logistics_metrics", {})
assert metrics.get("recommended_container") == "20ft Standard Container", metrics
assert metrics.get("total_weight_kg", 0) > 0, metrics
assert metrics.get("risk_level") in {"critical", "high"}, metrics

handoff = payload.get("handoff_payload", {})
assert handoff.get("destination") == "Germany" or handoff.get("destination_country") == "Germany", handoff

assert "unknown item" not in json.dumps(visualizer, default=str).lower(), visualizer

print("Avishi hazardous container API regression passed.")
print(json.dumps({
    "status": payload.get("status"),
    "detected_intent": payload.get("detected_intent"),
    "agents_called": agents,
    "destination": handoff.get("destination") or handoff.get("destination_country"),
    "logistics_metrics": metrics,
    "visualizer_status": visualizer.get("status"),
    "cargo_mix": cargo_mix,
}, indent=2, default=str))
