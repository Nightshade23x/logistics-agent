from __future__ import annotations

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

LIVE_URL = os.getenv("TRADE_ORCHESTRATOR_BASE_URL", "").strip()

PROMPT = (
    "estimate freight and find supplier for 100 ceramic tiles from India to USA. "
    "Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. "
    "Duty rate is 5 percent. Import tax rate is 8 percent."
)

if len(sys.argv) > 1:
    PROMPT = " ".join(sys.argv[1:])


def _partner_review(response: dict[str, Any]) -> dict[str, Any]:
    partner = response.get("partner_review")
    if isinstance(partner, dict):
        return partner

    specialist = response.get("specialist_responses")
    if isinstance(specialist, dict) and isinstance(specialist.get("partner_review_service"), dict):
        return specialist["partner_review_service"]

    return {}


def main() -> int:
    if not LIVE_URL:
        print(
            "SKIPPED: TRADE_ORCHESTRATOR_BASE_URL is not set. "
            "Set it when Avishi's orchestrator is running, for example:\n"
            '$env:TRADE_ORCHESTRATOR_BASE_URL = "http://127.0.0.1:8010"'
        )
        return 0

    os.environ["USE_TRAINED_ROUTER"] = "1"
    os.environ["ENABLE_TRADER_AGENT"] = "1"

    from app.user_agent import run_user_agent_from_text

    response = run_user_agent_from_text(PROMPT)

    partner = _partner_review(response)
    partner_payload = response.get("partner_review_payload") or {}

    summary = {
        "prompt": PROMPT,
        "live_url": LIVE_URL,
        "status": response.get("status"),
        "agents_called": response.get("agents_called"),
        "review_services_called": response.get("review_services_called"),
        "partner_review_status": response.get("partner_review_status"),
        "partner_review_attempted": response.get("partner_review_attempted"),
        "partner_review_mode": response.get("partner_review_mode"),
        "partner_review_service_called": response.get("partner_review_service_called"),
        "live_orchestrator_configured": response.get("live_orchestrator_configured"),
        "partner_review_keys": list(partner.keys()),
        "partner_review_summary": partner.get("summary"),
        "partner_review_verdict": partner.get("verdict") or partner.get("final_verdict"),
        "partner_payload": {
            "origin": partner_payload.get("origin"),
            "origin_country": partner_payload.get("origin_country"),
            "destination": partner_payload.get("destination"),
            "destination_country": partner_payload.get("destination_country"),
            "incoterm": partner_payload.get("incoterm"),
            "freight_quote_usd": partner_payload.get("freight_quote_usd"),
            "insurance_premium_usd": partner_payload.get("insurance_premium_usd"),
            "duty_rate_percent": partner_payload.get("duty_rate_percent"),
            "import_tax_rate_percent": partner_payload.get("import_tax_rate_percent"),
            "total_cbm": partner_payload.get("total_cbm"),
            "total_weight_kg": partner_payload.get("total_weight_kg"),
        },
    }

    print(json.dumps(summary, indent=2, default=str))

    assert "shopping_agent" in (response.get("agents_called") or []), "Shopping Agent was not called."
    assert "logistics_agent" in (response.get("agents_called") or []), "Logistics Agent was not called."
    assert "partner_review_service" in (response.get("review_services_called") or []), "Partner review service was not recorded."

    assert response.get("partner_review_attempted") is True, "Partner review was not attempted."
    assert response.get("partner_review_service_called") is True, "Partner review service was not marked as called."
    assert response.get("partner_review_mode") == "live_orchestrator", "Partner review did not use live orchestrator mode."
    assert response.get("live_orchestrator_configured") is True, "Live orchestrator was not marked configured."

    assert partner, "No partner_review payload was returned."
    assert partner_payload.get("origin") == "India", "Partner payload origin missing/wrong."
    assert partner_payload.get("destination") == "USA", "Partner payload destination missing/wrong."
    assert partner_payload.get("incoterm") == "CIF", "Partner payload incoterm missing/wrong."
    assert partner_payload.get("freight_quote_usd") == 1200.0, "Partner payload freight quote missing/wrong."
    assert partner_payload.get("insurance_premium_usd") == 250.0, "Partner payload insurance premium missing/wrong."
    assert partner_payload.get("duty_rate_percent") == 5.0, "Partner payload duty rate missing/wrong."
    assert partner_payload.get("import_tax_rate_percent") == 8.0, "Partner payload import tax rate missing/wrong."

    print("\nLIVE ORCHESTRATOR PIPELINE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
