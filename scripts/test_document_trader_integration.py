from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

os.environ["ENABLE_TRADER_AGENT"] = "1"

ROOT_DIR = Path(__file__).resolve().parents[1]

from app.user_agent import run_user_agent_from_files

response = run_user_agent_from_files(
    [
        ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
        ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
    ]
)

trader = response.get("specialist_responses", {}).get("trader_agent", {})

print(json.dumps({
    "status": response.get("status"),
    "agents_called": response.get("agents_called"),
    "specialist_response_keys": list(response.get("specialist_responses", {}).keys()),
    "trader_status": trader.get("status"),
    "trader_has_llm_judgment": "llm_judgment" in str(trader.get("report", "")),
    "trader_input": response.get("trader_input"),
    "missing_information": response.get("missing_information"),
}, indent=2, default=str))
