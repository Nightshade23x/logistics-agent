from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api_server import app

OUT = Path("demo_outputs/backend_payload_polish")
OUT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

tests = [
    {
        "name": "prompt1_hazardous_documents_not_empty",
        "prompt": "20ft container of hazardous chemicals, destination Germany",
        "checks": "hazardous_short",
    },
    {
        "name": "prompt3_visualizer_display_dimensions",
        "prompt": "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
        "checks": "visualizer_dimensions",
    },
    {
        "name": "prompt7_finance_visible",
        "prompt": "Finance Agent: calculate landed cost for ceramic tiles from India to USA using CIF. Procurement value 12000 USD, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent, customs brokerage 400 USD, local delivery 800 USD. Total cargo is 10 CBM and 1200 kg.",
        "checks": "finance",
    },
    {
        "name": "prompt8_hazardous_documents",
        "prompt": "What documents are needed to ship hazardous chemicals from India to Germany using CIF? Include dangerous goods declaration, MSDS, insurance, and compliance readiness.",
        "checks": "documents",
    },
]

summary = []

for test in tests:
    response = client.post("/api/request/text", json={"user_text": test["prompt"], "include_raw_response": True})
    assert response.status_code == 200, response.text[:2000]

    payload = response.json()
    path = OUT / f"{test['name']}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    problems = []
    dumped = json.dumps(payload, default=str).lower()

    doc = payload.get("document_requirements_advice") if isinstance(payload.get("document_requirements_advice"), dict) else {}
    comp = payload.get("trade_compliance_readiness") if isinstance(payload.get("trade_compliance_readiness"), dict) else {}
    landed = payload.get("landed_cost_advice") if isinstance(payload.get("landed_cost_advice"), dict) else {}
    known = landed.get("known_inputs") if isinstance(landed.get("known_inputs"), dict) else {}
    vis = payload.get("logistics_visualizer") if isinstance(payload.get("logistics_visualizer"), dict) else {}

    if test["checks"] == "hazardous_short":
        if doc.get("item_count", 0) < 1:
            problems.append("document item_count still 0")
        if "msds" not in dumped:
            problems.append("MSDS missing")
        if "dangerous goods declaration" not in dumped:
            problems.append("dangerous goods declaration missing")
        if "no shipment items were available" in dumped or "no shipment items were found" in dumped:
            problems.append("stale no-shipment-items text still present")
        if "which products and quantities are included" in dumped:
            problems.append("stale product quantity question still present")

    if test["checks"] == "visualizer_dimensions":
        cargo_mix = vis.get("cargo_mix") if isinstance(vis.get("cargo_mix"), list) else []
        for item in cargo_mix:
            dims = item.get("dimensions_m") if isinstance(item, dict) else {}
            if isinstance(dims, dict):
                length = float(dims.get("length") or 0)
                width = float(dims.get("width") or 0)
                height = float(dims.get("height") or 0)
                if length > 5.8 or width > 2.35 or height > 2.35:
                    problems.append(f"oversized visualizer dims for {item.get('item_name')}: {dims}")

    if test["checks"] == "finance":
        required = {
            "procurement_value_usd": 12000,
            "freight_quote_usd": 3500,
            "insurance_premium_usd": 600,
            "duty_rate_percent": 8,
            "import_tax_rate_percent": 6,
            "customs_brokerage_usd": 400,
            "local_delivery_usd": 800,
        }

        for key, expected in required.items():
            actual = known.get(key)
            try:
                ok = abs(float(actual) - expected) < 0.01
            except Exception:
                ok = False
            if not ok:
                problems.append(f"{key} expected {expected}, got {actual}")

        if landed.get("status") == "blocked":
            problems.append("landed cost still blocked")

        if landed.get("estimated_landed_cost_usd") is None and landed.get("estimated_subtotal_known_usd") is None:
            problems.append("estimated landed cost missing")

        if "finance_agent" not in (payload.get("agents_called") or []):
            problems.append("finance_agent not listed")

    if test["checks"] == "documents":
        if doc.get("origin_country") != "India":
            problems.append(f"origin expected India, got {doc.get('origin_country')}")
        if doc.get("destination_country") != "Germany":
            problems.append(f"destination expected Germany, got {doc.get('destination_country')}")
        if doc.get("item_count", 0) < 1:
            problems.append("document item_count still 0")
        if "msds" not in dumped:
            problems.append("MSDS missing")
        if "dangerous goods declaration" not in dumped:
            problems.append("dangerous goods declaration missing")
        if "document_ai_agent" not in (payload.get("agents_called") or []):
            problems.append("document_ai_agent not listed")

    item = {
        "name": test["name"],
        "status": "PASS" if not problems else "FAIL",
        "detected_intent": payload.get("detected_intent"),
        "agents_called": payload.get("agents_called"),
        "doc_item_count": doc.get("item_count"),
        "doc_origin": doc.get("origin_country"),
        "doc_destination": doc.get("destination_country"),
        "landed_status": landed.get("status"),
        "estimated_landed_cost_usd": landed.get("estimated_landed_cost_usd") or landed.get("estimated_subtotal_known_usd"),
        "problems": problems,
        "json_path": str(path),
    }

    summary.append(item)
    print(json.dumps(item, indent=2, default=str))

summary_path = OUT / "BACKEND_PAYLOAD_POLISH_SUMMARY.json"
summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

failures = [item for item in summary if item["status"] == "FAIL"]

print()
print("BACKEND PAYLOAD POLISH SUMMARY")
for item in summary:
    print(f"{item['status']}: {item['name']} | agents={item.get('agents_called')} | landed={item.get('landed_status')} | doc_items={item.get('doc_item_count')}")

print(f"\nSaved: {summary_path}")

if failures:
    raise SystemExit(1)

print("\nBACKEND PAYLOAD POLISH PASSED.")
