import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api_server import app

OUT = Path("demo_outputs/backend_payload_polish_v2")
OUT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

tests = [
    {
        "name": "prompt1_hazardous_short",
        "prompt": "20ft container of hazardous chemicals, destination Germany",
        "type": "hazardous_short",
    },
    {
        "name": "prompt3_shopping_no_false_hazard",
        "prompt": "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
        "type": "shopping_clean",
    },
    {
        "name": "prompt7_finance_no_false_hazard",
        "prompt": "Finance Agent: calculate landed cost for ceramic tiles from India to USA using CIF. Procurement value 12000 USD, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent, customs brokerage 400 USD, local delivery 800 USD. Total cargo is 10 CBM and 1200 kg.",
        "type": "finance",
    },
    {
        "name": "prompt8_docs_hazardous",
        "prompt": "What documents are needed to ship hazardous chemicals from India to Germany using CIF? Include dangerous goods declaration, MSDS, insurance, and compliance readiness.",
        "type": "docs_hazardous",
    },
]

def dump_lower(payload):
    return json.dumps(payload, default=str).lower()

def get_doc(payload):
    return payload.get("document_requirements_advice") if isinstance(payload.get("document_requirements_advice"), dict) else {}

def get_comp(payload):
    return payload.get("trade_compliance_readiness") if isinstance(payload.get("trade_compliance_readiness"), dict) else {}

def get_landed(payload):
    return payload.get("landed_cost_advice") if isinstance(payload.get("landed_cost_advice"), dict) else {}

summary = []

for test in tests:
    response = client.post("/api/request/text", json={"user_text": test["prompt"], "include_raw_response": True})
    assert response.status_code == 200, response.text[:2000]

    payload = response.json()
    out_path = OUT / f"{test['name']}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    problems = []
    text = dump_lower(payload)
    doc = get_doc(payload)
    comp = get_comp(payload)
    landed = get_landed(payload)
    known = landed.get("known_inputs") if isinstance(landed.get("known_inputs"), dict) else {}
    agents = payload.get("agents_called") or []

    if test["type"] == "hazardous_short":
        if "compression" in str(doc.get("origin_country")).lower() or "compression" in str(comp.get("origin_country")).lower():
            problems.append("origin polluted as compression")
        if doc.get("incoterm") == "EXW" or comp.get("incoterm") == "EXW":
            problems.append("incoterm falsely inferred as EXW")
        if doc.get("destination_country") != "Germany":
            problems.append(f"destination expected Germany, got {doc.get('destination_country')}")
        if doc.get("item_count", 0) < 1:
            problems.append("document item_count should be at least 1")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazardous docs missing")
        if "no shipment items were available" in text or "no shipment items were found" in text:
            problems.append("stale no shipment item text present")

    if test["type"] == "shopping_clean":
        for extra in ["document_ai_agent", "compliance_agent", "risk_agent"]:
            if extra in agents:
                problems.append(f"extra agent injected: {extra}")
        for bad in ["possible hazardous cargo", "dangerous goods declaration", "msds", "carrier dangerous-goods"]:
            if bad in text:
                problems.append(f"false hazardous text present: {bad}")
        if doc.get("item_count") != 4:
            problems.append(f"doc item_count expected 4, got {doc.get('item_count')}")

    if test["type"] == "finance":
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
            problems.append("finance still blocked")
        if landed.get("estimated_landed_cost_usd") is None and landed.get("estimated_subtotal_known_usd") is None:
            problems.append("estimated landed cost missing")
        for bad in ["possible hazardous cargo", "dangerous goods declaration", "msds", "carrier dangerous-goods"]:
            if bad in text:
                problems.append(f"false hazardous text present: {bad}")

    if test["type"] == "docs_hazardous":
        if "document_ai_agent" not in agents:
            problems.append("document_ai_agent missing")
        if "compliance_agent" not in agents:
            problems.append("compliance_agent missing")
        if doc.get("origin_country") != "India":
            problems.append(f"doc origin expected India, got {doc.get('origin_country')}")
        if doc.get("destination_country") != "Germany":
            problems.append(f"doc destination expected Germany, got {doc.get('destination_country')}")
        if doc.get("incoterm") != "CIF":
            problems.append(f"doc incoterm expected CIF, got {doc.get('incoterm')}")
        if doc.get("item_count", 0) < 1:
            problems.append("doc item_count should be at least 1")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazardous docs missing")
        for bad in ["origin country is missing", "destination country is missing", "origin_country", "destination_country"]:
            if bad in text and bad in ["origin country is missing", "destination country is missing"]:
                problems.append(f"stale missing route text present: {bad}")

    item = {
        "name": test["name"],
        "status": "PASS" if not problems else "FAIL",
        "detected_intent": payload.get("detected_intent"),
        "agents_called": agents,
        "doc_origin": doc.get("origin_country"),
        "doc_destination": doc.get("destination_country"),
        "doc_incoterm": doc.get("incoterm"),
        "doc_item_count": doc.get("item_count"),
        "landed_status": landed.get("status"),
        "estimated_landed_cost": landed.get("estimated_landed_cost_usd") or landed.get("estimated_subtotal_known_usd"),
        "problems": problems,
        "json_path": str(out_path),
    }
    summary.append(item)
    print(json.dumps(item, indent=2, default=str))

summary_path = OUT / "BACKEND_RESPONSE_POLISH_V2_SUMMARY.json"
summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

print()
print("BACKEND RESPONSE POLISH V2 SUMMARY")
for item in summary:
    print(f"{item['status']}: {item['name']} | agents={item['agents_called']} | doc_origin={item['doc_origin']} | doc_dest={item['doc_destination']} | item_count={item['doc_item_count']} | landed={item['landed_status']}")

print(f"\nSaved: {summary_path}")

if any(item["status"] == "FAIL" for item in summary):
    raise SystemExit(1)

print("\nBACKEND RESPONSE POLISH V2 PASSED.")
