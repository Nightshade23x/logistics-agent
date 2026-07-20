from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

os.environ["USE_TRAINED_ROUTER"] = "1"

from app.user_agent import run_user_agent_from_text

response = run_user_agent_from_text(
    "assess trade plan for ceramic tiles from India to USA"
)

trader = response.get("specialist_responses", {}).get("trader_agent", {})

result = {
    "status": response.get("status"),
    "detected_intent": response.get("detected_intent"),
    "agents_called": response.get("agents_called"),
    "trader_input": response.get("trader_input"),
    "trader_status": trader.get("status"),
    "trader_has_llm_judgment": "llm_judgment" in str(trader.get("report", "")),
    "missing_information": response.get("missing_information"),
}

print(json.dumps(result, indent=2, default=str))

assert response.get("detected_intent") == "trader"
assert response.get("agents_called") == ["trader_agent"]
assert result["trader_has_llm_judgment"] is True
assert response.get("trader_input", {}).get("country_from") == "India"
assert response.get("trader_input", {}).get("country_to") == "USA"

print("\nDIRECT TRADER ROUTING CHECK PASSED")
