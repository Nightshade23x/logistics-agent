from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

os.environ["USE_TRAINED_ROUTER"] = "1"
os.environ["ENABLE_TRADER_AGENT"] = "1"

ROOT_DIR = Path(__file__).resolve().parents[1]

from app.user_agent import run_user_agent_from_files, run_user_agent_from_text


def summarize_response(name: str, response: dict) -> dict:
    trader = response.get("specialist_responses", {}).get("trader_agent", {})
    return {
        "flow": name,
        "status": response.get("status"),
        "agents_called": response.get("agents_called"),
        "specialist_response_keys": list(response.get("specialist_responses", {}).keys()),
        "trader_status": trader.get("status"),
        "trader_has_llm_judgment": "llm_judgment" in str(trader.get("report", "")),
        "trader_input": response.get("trader_input"),
        "missing_information": response.get("missing_information"),
    }


shopping_flow = run_user_agent_from_text(
    "estimate freight and find supplier for 100 ceramic tiles from India to USA"
)

document_flow = run_user_agent_from_files(
    [
        ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
        ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
    ]
)

results = [
    summarize_response("shopping_to_logistics_to_trader", shopping_flow),
    summarize_response("document_to_logistics_to_trader", document_flow),
]

print(json.dumps(results, indent=2, default=str))

for result in results:
    assert "trader_agent" in result["agents_called"], result
    assert result["trader_has_llm_judgment"] is True, result

print("\nFULL TRADER INTEGRATION CHECK PASSED")
