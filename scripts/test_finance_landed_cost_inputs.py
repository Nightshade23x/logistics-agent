from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api_server import app

OUT = Path("demo_outputs/full_system_tests")
OUT.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Finance Agent: calculate landed cost for ceramic tiles from India to USA using CIF. "
    "Procurement value 12000 USD, freight quote 3500 USD, insurance 600 USD, "
    "duty 8 percent, import tax 6 percent, customs brokerage 400 USD, "
    "local delivery 800 USD. Total cargo is 10 CBM and 1200 kg."
)

client = TestClient(app)
response = client.post(
    "/api/request/text",
    json={"user_text": PROMPT, "include_raw_response": True},
)

assert response.status_code == 200, response.text[:2000]
payload = response.json()

out_path = OUT / "finance_landed_cost_after_fix.json"
out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

advice = payload.get("landed_cost_advice") or {}
known = advice.get("known_inputs") or {}
missing = advice.get("missing_cost_inputs") or []
dumped = json.dumps(payload, default=str).lower()

required_known = {
    "procurement_value_usd": 12000,
    "freight_quote_usd": 3500,
    "insurance_premium_usd": 600,
    "duty_rate_percent": 8,
    "import_tax_rate_percent": 6,
    "customs_brokerage_usd": 400,
    "local_delivery_usd": 800,
}

problems = []

if advice.get("status") == "blocked":
    problems.append("landed_cost_advice is still blocked")

for key, expected in required_known.items():
    actual = known.get(key)
    try:
        actual_float = float(actual)
    except Exception:
        problems.append(f"{key} missing/non-numeric in known_inputs: {actual}")
        continue

    if abs(actual_float - expected) > 0.01:
        problems.append(f"{key} expected {expected}, got {actual_float}")

for key in ["procurement_value_usd", "customs_brokerage_usd", "local_delivery_usd"]:
    if key in missing:
        problems.append(f"{key} still listed as missing")

if advice.get("estimated_subtotal_known_usd") is None and advice.get("estimated_landed_cost_usd") is None:
    problems.append("no estimated landed cost/subtotal produced")

if "procurement value or declared value is missing" in dumped:
    problems.append("old procurement blocker text still appears")

if problems:
    print(json.dumps({
        "status": "FAIL",
        "problems": problems,
        "detected_intent": payload.get("detected_intent"),
        "agents_called": payload.get("agents_called"),
        "landed_cost_advice": advice,
        "json_path": str(out_path),
    }, indent=2, default=str))
    raise SystemExit(1)

print(json.dumps({
    "status": "PASS",
    "detected_intent": payload.get("detected_intent"),
    "top_status": payload.get("status"),
    "agents_called": payload.get("agents_called"),
    "landed_cost_status": advice.get("status"),
    "known_inputs": known,
    "missing_cost_inputs": missing,
    "estimated_subtotal_known_usd": advice.get("estimated_subtotal_known_usd"),
    "estimated_landed_cost_usd": advice.get("estimated_landed_cost_usd"),
    "json_path": str(out_path),
}, indent=2, default=str))
