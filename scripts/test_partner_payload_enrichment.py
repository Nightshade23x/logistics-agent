from __future__ import annotations

import json
import os

os.environ["USE_TRAINED_ROUTER"] = "1"
os.environ["ENABLE_TRADER_AGENT"] = "1"
os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

from app.user_agent import run_user_agent_from_text

PROMPT = (
    "estimate freight and find supplier for 100 ceramic tiles from India to USA. "
    "Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. "
    "Duty rate is 5 percent. Import tax rate is 8 percent."
)

response = run_user_agent_from_text(PROMPT)

partner_payload = response.get("partner_review_payload") or {}
partner_review = response.get("partner_review") or {}
missing_required_fields = partner_review.get("missing_required_fields") or []

summary = {
    "status": response.get("status"),
    "agents_called": response.get("agents_called"),
    "review_services_called": response.get("review_services_called"),
    "partner_review_status": response.get("partner_review_status"),
    "partner_review_mode": response.get("partner_review_mode"),
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
    },
    "partner_missing_required_fields": missing_required_fields,
}

print(json.dumps(summary, indent=2, default=str))

assert partner_payload.get("origin") == "India"
assert partner_payload.get("origin_country") == "India"
assert partner_payload.get("destination") == "USA"
assert partner_payload.get("destination_country") == "USA"
assert partner_payload.get("incoterm") == "CIF"
assert partner_payload.get("freight_quote_usd") == 1200.0
assert partner_payload.get("insurance_premium_usd") == 250.0
assert partner_payload.get("duty_rate_percent") == 5.0
assert partner_payload.get("import_tax_rate_percent") == 8.0
assert not any("destination" in str(field).lower() for field in missing_required_fields)

print("\nPARTNER PAYLOAD ENRICHMENT CHECK PASSED")
