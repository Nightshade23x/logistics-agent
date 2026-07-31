import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api_server import app

OUT = Path("demo_outputs/backend_consistency_v6")
OUT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

tests = [
    {
        "name": "prompt1_hazardous_short",
        "prompt": "20ft container of hazardous chemicals, destination Germany",
    },
    {
        "name": "prompt2_aggregate_tiles",
        "prompt": "Ship 10 pallets of ceramic tiles from India to USA using CIF. Total cargo is 10 CBM and 1200 kg.",
    },
    {
        "name": "prompt3_mixed_shopping_visualizer",
        "prompt": "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
    },
    {
        "name": "prompt4_finance",
        "prompt": "Finance Agent: calculate landed cost for ceramic tiles from India to USA using CIF. Procurement value 12000 USD, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent, customs brokerage 400 USD, local delivery 800 USD. Total cargo is 10 CBM and 1200 kg.",
    },
    {
        "name": "prompt5_docs_hazardous",
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

    problems = []
    text = json.dumps(payload, default=str).lower()

    agents = payload.get("agents_called") or []
    doc = payload.get("document_requirements_advice") if isinstance(payload.get("document_requirements_advice"), dict) else {}
    landed = payload.get("landed_cost_advice") if isinstance(payload.get("landed_cost_advice"), dict) else {}
    vis = payload.get("logistics_visualizer") if isinstance(payload.get("logistics_visualizer"), dict) else {}
    fit = vis.get("fit_check") if isinstance(vis.get("fit_check"), dict) else {}

    if test["name"] == "prompt1_hazardous_short":
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazard docs missing")

    if test["name"] == "prompt2_aggregate_tiles":
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        if agents != ["logistics_agent", "trader_agent"]:
            problems.append(f"agents expected logistics/trader only, got {agents}")

    if test["name"] == "prompt3_mixed_shopping_visualizer":
        expected_agents = ["shopping_agent", "logistics_agent", "trader_agent"]
        if agents != expected_agents:
            problems.append(f"agents expected {expected_agents}, got {agents}")
        if doc.get("item_count") != 4:
            problems.append(f"doc item_count expected 4, got {doc.get('item_count')}")
        for bad in ["dangerous goods declaration", "msds", "possible hazardous cargo"]:
            if bad in text:
                problems.append(f"false hazardous text: {bad}")
        for bad in ["ceramic tiles: may not physically fit", "switching to 40ft standard container solves"]:
            if bad in text:
                problems.append(f"stale fit text: {bad}")
        if fit.get("status") != "fits_selected_container":
            problems.append(f"fit status expected fits_selected_container, got {fit.get('status')}")

    if test["name"] == "prompt4_finance":
        if agents != ["trader_agent", "finance_agent"]:
            problems.append(f"agents expected trader/finance, got {agents}")
        if landed.get("status") == "blocked":
            problems.append("landed cost still blocked")
        if landed.get("estimated_landed_cost_usd") is None and landed.get("estimated_subtotal_known_usd") is None:
            problems.append("landed cost estimate missing")
        if "Agents called: trader_agent, finance_agent" not in str(payload.get("short_answer", "")):
            problems.append("short_answer did not sync finance_agent")

    if test["name"] == "prompt5_docs_hazardous":
        if agents != ["document_ai_agent", "compliance_agent"]:
            problems.append(f"agents expected document/compliance, got {agents}")
        if doc.get("item_count") != 1:
            problems.append(f"doc item_count expected 1, got {doc.get('item_count')}")
        if doc.get("origin_country") != "India" or doc.get("destination_country") != "Germany" or doc.get("incoterm") != "CIF":
            problems.append(f"route wrong: {doc.get('origin_country')}->{doc.get('destination_country')} {doc.get('incoterm')}")
        if "msds" not in text or "dangerous goods declaration" not in text:
            problems.append("hazard docs missing")
        if "Agents called: document_ai_agent, compliance_agent" not in str(payload.get("short_answer", "")):
            problems.append("short_answer did not sync document/compliance agents")

    item = {
        "name": test["name"],
        "status": "PASS" if not problems else "FAIL",
        "agents_called": agents,
        "short_answer": payload.get("short_answer"),
        "doc_item_count": doc.get("item_count"),
        "doc_origin": doc.get("origin_country"),
        "doc_destination": doc.get("destination_country"),
        "doc_incoterm": doc.get("incoterm"),
        "visualizer_status": vis.get("status"),
        "fit_status": fit.get("status"),
        "fit_warnings": fit.get("warnings"),
        "landed_status": landed.get("status"),
        "estimated_landed_cost": landed.get("estimated_landed_cost_usd") or landed.get("estimated_subtotal_known_usd"),
        "problems": problems,
        "json_path": str(out_path),
    }

    summary.append(item)
    print(json.dumps(item, indent=2, default=str))

summary_path = OUT / "BACKEND_CONSISTENCY_V6_SUMMARY.json"
summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

print()
print("BACKEND CONSISTENCY V6 SUMMARY")
for item in summary:
    print(f"{item['status']}: {item['name']} | agents={item['agents_called']} | items={item['doc_item_count']} | fit={item['fit_status']} | landed={item['landed_status']}")

print(f"\nSaved: {summary_path}")

if any(item["status"] == "FAIL" for item in summary):
    raise SystemExit(1)

print("\nBACKEND CONSISTENCY V6 PASSED.")
