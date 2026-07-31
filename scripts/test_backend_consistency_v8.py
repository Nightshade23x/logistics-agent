import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api_server import app

OUT = Path("demo_outputs/backend_consistency_v8")
OUT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

tests = [
    {
        "name": "p1_hazardous_short",
        "prompt": "20ft container of hazardous chemicals, destination Germany",
    },
    {
        "name": "p2_tiles",
        "prompt": "Ship 10 pallets of ceramic tiles from India to USA using CIF. Total cargo is 10 CBM and 1200 kg.",
    },
    {
        "name": "p3_mixed_shopping",
        "prompt": "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
    },
    {
        "name": "p4_finance_tiles",
        "prompt": "Finance Agent: calculate landed cost for ceramic tiles from India to USA using CIF. Procurement value 12000 USD, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent, customs brokerage 400 USD, local delivery 800 USD. Total cargo is 10 CBM and 1200 kg.",
    },
    {
        "name": "p5_docs_hazardous",
        "prompt": "What documents are needed to ship hazardous chemicals from India to Germany using CIF? Include dangerous goods declaration, MSDS, insurance, and compliance readiness.",
    },
    {
        "name": "p6_tvs_scooters",
        "prompt": "Ship 50 TVs and 5 electric scooters from India to USA using CIF. TVs are fragile and scooters have batteries. Freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent.",
    },
    {
        "name": "p7_cotton_pillows",
        "prompt": "Find suppliers and shipping plan for 200 cotton pillows from India to Germany using FOB.",
    },
    {
        "name": "p8_radioactive",
        "prompt": "Ship radioactive lab equipment from India to Germany using DDP. Total cargo is 3 CBM and 500 kg.",
    },
    {
        "name": "p9_finance_mattresses",
        "prompt": "Calculate landed cost for mattresses from Turkey to USA using DAP. Procurement value 9000 USD, freight quote 2200 USD, insurance 300 USD, duty 6 percent, import tax 5 percent, customs brokerage 350 USD, local delivery 700 USD.",
    },
]

summary = []

for test in tests:
    response = client.post("/api/request/text", json={"user_text": test["prompt"], "include_raw_response": True})
    assert response.status_code == 200, response.text[:2000]

    payload = response.json()
    text = json.dumps(payload, default=str).lower()

    out_path = OUT / f"{test['name']}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    agents = payload.get("agents_called") or []
    metrics = payload.get("logistics_metrics") if isinstance(payload.get("logistics_metrics"), dict) else {}
    visualizer = payload.get("logistics_visualizer") if isinstance(payload.get("logistics_visualizer"), dict) else {}
    doc = payload.get("document_requirements_advice") if isinstance(payload.get("document_requirements_advice"), dict) else {}
    landed = payload.get("landed_cost_advice") if isinstance(payload.get("landed_cost_advice"), dict) else {}

    problems = []

    if test["name"] == "p1_hazardous_short":
        if agents != ["logistics_agent"]:
            problems.append(f"expected logistics_agent only, got {agents}")
        if metrics.get("total_cbm") != 1.2 or metrics.get("total_weight_kg") != 1000:
            problems.append(f"bad metrics {metrics}")
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazard documents missing")

    if test["name"] == "p2_tiles":
        if agents != ["logistics_agent", "trader_agent"]:
            problems.append(f"expected logistics/trader, got {agents}")
        if metrics.get("total_cbm") != 10 or metrics.get("total_weight_kg") != 1200:
            problems.append(f"bad metrics {metrics}")
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")

    if test["name"] == "p3_mixed_shopping":
        if agents != ["shopping_agent", "logistics_agent", "trader_agent"]:
            problems.append(f"expected shopping/logistics/trader, got {agents}")
        if doc.get("item_count") != 4:
            problems.append(f"doc item_count expected 4, got {doc.get('item_count')}")
        for bad in ["may not physically fit", "switching to 40ft standard container", "msds", "dangerous goods declaration", "possible hazardous cargo"]:
            if bad in text:
                problems.append(f"bad stale/hazard text: {bad}")

    if test["name"] == "p4_finance_tiles":
        if agents != ["trader_agent", "finance_agent"]:
            problems.append(f"expected trader/finance, got {agents}")
        if landed.get("estimated_landed_cost_usd") != 19631.28:
            problems.append(f"bad landed cost {landed.get('estimated_landed_cost_usd')}")
        if landed.get("missing_cost_inputs"):
            problems.append(f"missing cost inputs {landed.get('missing_cost_inputs')}")

    if test["name"] == "p5_docs_hazardous":
        if agents != ["document_ai_agent", "compliance_agent"]:
            problems.append(f"expected document/compliance, got {agents}")
        if doc.get("origin_country") != "India" or doc.get("destination_country") != "Germany" or doc.get("incoterm") != "CIF":
            problems.append(f"bad route {doc.get('origin_country')}->{doc.get('destination_country')} {doc.get('incoterm')}")
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazard documents missing")

    if test["name"] == "p6_tvs_scooters":
        if agents != ["logistics_agent", "trader_agent"]:
            problems.append(f"expected logistics/trader, got {agents}")
        if metrics.get("risk_level") != "critical":
            problems.append(f"expected critical risk, got {metrics.get('risk_level')}")
        if doc.get("item_count") != 2:
            problems.append(f"doc item_count expected 2, got {doc.get('item_count')}")
        if "electric scooters" not in text or "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("battery/hazard text missing")

    if test["name"] == "p7_cotton_pillows":
        if agents != ["shopping_agent", "logistics_agent", "trader_agent"]:
            problems.append(f"expected shopping/logistics/trader, got {agents}")
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        for bad in ["msds", "dangerous goods declaration", "possible hazardous cargo", "pillows: fragile", "fragile handling / packing declaration"]:
            if bad in text:
                problems.append(f"bad false warning: {bad}")

    if test["name"] == "p8_radioactive":
        if agents != ["logistics_agent", "trader_agent"]:
            problems.append(f"expected logistics/trader, got {agents}")
        if metrics.get("risk_level") != "critical" or metrics.get("total_cbm") != 3 or metrics.get("total_weight_kg") != 500:
            problems.append(f"bad radioactive metrics {metrics}")
        if visualizer.get("status") != "available":
            problems.append(f"visualizer expected available, got {visualizer.get('status')}")
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        for required in ["radioactive material declaration", "carrier radioactive-material acceptance confirmation"]:
            if required not in text:
                problems.append(f"missing radioactive document: {required}")
        for bad in ["agents called: .", "no shipment items were found", "no shipment items were available"]:
            if bad in text:
                problems.append(f"stale radioactive text: {bad}")

    if test["name"] == "p9_finance_mattresses":
        if agents != ["trader_agent", "finance_agent"]:
            problems.append(f"expected trader/finance, got {agents}")
        if landed.get("estimated_landed_cost_usd") != 13849.5:
            problems.append(f"bad landed cost {landed.get('estimated_landed_cost_usd')}")
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        for bad in ["no shipment items were found", "no shipment items were available"]:
            if bad in text:
                problems.append(f"stale no-item text: {bad}")

    row = {
        "name": test["name"],
        "status": "PASS" if not problems else "FAIL",
        "agents_called": agents,
        "top_status": payload.get("status"),
        "intent": payload.get("detected_intent"),
        "metrics": metrics,
        "visualizer_status": visualizer.get("status"),
        "doc_item_count": doc.get("item_count"),
        "landed_cost": landed.get("estimated_landed_cost_usd"),
        "problems": problems,
        "json_path": str(out_path),
    }

    summary.append(row)
    print(json.dumps(row, indent=2, default=str))

summary_path = OUT / "BACKEND_CONSISTENCY_V8_SUMMARY.json"
summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

print()
print("BACKEND CONSISTENCY V8 SUMMARY")
for row in summary:
    print(f"{row['status']}: {row['name']} | agents={row['agents_called']} | items={row['doc_item_count']} | visualizer={row['visualizer_status']} | landed={row['landed_cost']}")

print(f"\nSaved: {summary_path}")

if any(row["status"] == "FAIL" for row in summary):
    raise SystemExit(1)

print("\nBACKEND CONSISTENCY V8 PASSED.")
