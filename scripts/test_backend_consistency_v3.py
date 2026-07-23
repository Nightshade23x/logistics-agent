import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api_server import app

OUT = Path("demo_outputs/backend_consistency_v3")
OUT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

tests = [
    {
        "name": "prompt1_hazardous_short",
        "prompt": "20ft container of hazardous chemicals, destination Germany",
    },
    {
        "name": "prompt2_mixed_shopping",
        "prompt": "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
    },
    {
        "name": "prompt3_finance",
        "prompt": "Finance Agent: calculate landed cost for ceramic tiles from India to USA using CIF. Procurement value 12000 USD, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent, customs brokerage 400 USD, local delivery 800 USD. Total cargo is 10 CBM and 1200 kg.",
    },
    {
        "name": "prompt4_docs_hazardous",
        "prompt": "What documents are needed to ship hazardous chemicals from India to Germany using CIF? Include dangerous goods declaration, MSDS, insurance, and compliance readiness.",
    },
]

summary = []

for test in tests:
    r = client.post("/api/request/text", json={"user_text": test["prompt"], "include_raw_response": True})
    assert r.status_code == 200, r.text[:2000]

    payload = r.json()
    out_path = OUT / f"{test['name']}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    text = json.dumps(payload, default=str).lower()
    agents = payload.get("agents_called") or []
    doc = payload.get("document_requirements_advice") if isinstance(payload.get("document_requirements_advice"), dict) else {}
    comp = payload.get("trade_compliance_readiness") if isinstance(payload.get("trade_compliance_readiness"), dict) else {}
    landed = payload.get("landed_cost_advice") if isinstance(payload.get("landed_cost_advice"), dict) else {}
    known = landed.get("known_inputs") if isinstance(landed.get("known_inputs"), dict) else {}

    problems = []

    if test["name"] == "prompt1_hazardous_short":
        if doc.get("destination_country") != "Germany":
            problems.append(f"destination expected Germany, got {doc.get('destination_country')}")
        if doc.get("origin_country") in ["compression", "EXW"]:
            problems.append(f"bad origin: {doc.get('origin_country')}")
        if doc.get("incoterm") == "EXW":
            problems.append("false EXW incoterm")
        if doc.get("item_count", 0) < 1:
            problems.append("item_count should be at least 1")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazard docs missing")
        if payload.get("missing_information_count") == 0:
            problems.append("top-level missing_information_count should not be 0")

    if test["name"] == "prompt2_mixed_shopping":
        for agent in ["shopping_agent", "logistics_agent", "trader_agent"]:
            if agent not in agents:
                problems.append(f"missing agent {agent}")
        for extra in ["document_ai_agent", "compliance_agent", "risk_agent", "finance_agent"]:
            if extra in agents:
                problems.append(f"unexpected extra agent {extra}")
        for bad in ["dangerous goods declaration", "msds", "possible hazardous cargo"]:
            if bad in text:
                problems.append(f"false hazardous text: {bad}")
        if doc.get("item_count") != 4:
            problems.append(f"doc item_count expected 4, got {doc.get('item_count')}")

    if test["name"] == "prompt3_finance":
        if "finance_agent" not in agents:
            problems.append("finance_agent missing")
        if landed.get("status") == "blocked":
            problems.append("landed cost should not be blocked")
        if landed.get("estimated_landed_cost_usd") is None and landed.get("estimated_subtotal_known_usd") is None:
            problems.append("landed estimate missing")
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
        for bad in ["dangerous goods declaration", "msds", "possible hazardous cargo"]:
            if bad in text:
                problems.append(f"false hazardous text: {bad}")

    if test["name"] == "prompt4_docs_hazardous":
        if "document_ai_agent" not in agents:
            problems.append("document_ai_agent missing")
        if "compliance_agent" not in agents:
            problems.append("compliance_agent missing")
        if doc.get("origin_country") != "India":
            problems.append(f"origin expected India, got {doc.get('origin_country')}")
        if doc.get("destination_country") != "Germany":
            problems.append(f"destination expected Germany, got {doc.get('destination_country')}")
        if doc.get("incoterm") != "CIF":
            problems.append(f"incoterm expected CIF, got {doc.get('incoterm')}")
        if doc.get("item_count", 0) < 1:
            problems.append("item_count should be at least 1")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazard docs missing")
        for bad in ["incoterm or trade term such as", "exact item list and quantities", "unit dimensions or packed dimensions", "unit weight or total packed weight"]:
            if bad in text:
                problems.append(f"stale missing info text: {bad}")

    item = {
        "name": test["name"],
        "status": "PASS" if not problems else "FAIL",
        "agents_called": agents,
        "doc_origin": doc.get("origin_country"),
        "doc_destination": doc.get("destination_country"),
        "doc_incoterm": doc.get("incoterm"),
        "doc_item_count": doc.get("item_count"),
        "landed_status": landed.get("status"),
        "estimated_landed_cost": landed.get("estimated_landed_cost_usd") or landed.get("estimated_subtotal_known_usd"),
        "missing_information_count": payload.get("missing_information_count"),
        "missing_information_preview": payload.get("missing_information_preview"),
        "problems": problems,
        "json_path": str(out_path),
    }
    summary.append(item)
    print(json.dumps(item, indent=2, default=str))

summary_path = OUT / "BACKEND_CONSISTENCY_V3_SUMMARY.json"
summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

print()
print("BACKEND CONSISTENCY V3 SUMMARY")
for item in summary:
    print(f"{item['status']}: {item['name']} | agents={item['agents_called']} | doc={item['doc_origin']}->{item['doc_destination']} {item['doc_incoterm']} | items={item['doc_item_count']} | missing={item['missing_information_count']} | landed={item['landed_status']}")

print(f"\nSaved: {summary_path}")

if any(item["status"] == "FAIL" for item in summary):
    raise SystemExit(1)

print("\nBACKEND CONSISTENCY V3 PASSED.")
