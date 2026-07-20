from __future__ import annotations

import json
import os

os.environ["USE_TRAINED_ROUTER"] = "1"
os.environ.pop("ENABLE_TRADER_AGENT", None)
os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

from app.user_agent import run_user_agent_from_text

response = run_user_agent_from_text(
    "estimate freight and find supplier for 100 ceramic tiles from India to USA"
)

partner = (
    response.get("partner_review")
    or response.get("specialist_responses", {}).get("partner_review_service")
    or {}
)

summary = {
    "status": response.get("status"),
    "agents_called": response.get("agents_called"),
    "review_services_called": response.get("review_services_called"),
    "top_level_partner_review_status": response.get("partner_review_status"),
    "top_level_partner_review_attempted": response.get("partner_review_attempted"),
    "top_level_partner_review_mode": response.get("partner_review_mode"),
    "top_level_partner_review_service_called": response.get("partner_review_service_called"),
    "top_level_live_orchestrator_configured": response.get("live_orchestrator_configured"),
    "nested_partner_status": partner.get("status"),
    "nested_partner_review_attempted": partner.get("partner_review_attempted"),
    "nested_partner_review_mode": partner.get("partner_review_mode"),
    "nested_partner_review_service_called": partner.get("partner_review_service_called"),
    "nested_live_orchestrator_configured": partner.get("live_orchestrator_configured"),
}

print(json.dumps(summary, indent=2, default=str))

assert response.get("partner_review_attempted") is True
assert response.get("partner_review_mode") == "local_fallback"
assert response.get("partner_review_service_called") is True
assert response.get("live_orchestrator_configured") is False
assert "partner_review_service" in (response.get("review_services_called") or [])

print("\nUSER AGENT PARTNER OBSERVABILITY CHECK PASSED")
