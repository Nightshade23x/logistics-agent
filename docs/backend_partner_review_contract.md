# Backend Partner Review Contract

This document describes the backend partner-review handoff contract after the V5 router and Trader integration work.

## Backend entry paths covered

The backend supports partner-review payload generation from three User Agent entry paths:

1. Text request

```python
run_user_agent_from_text(...)
```

2. Uploaded document request

```python
run_user_agent_from_files(...)
```

3. JSON request

```python
run_user_agent_from_json(...)
```

These paths are covered by:

```powershell
python scripts\test_partner_payload_contract.py
```

The full backend health suite is:

```powershell
python scripts\run_backend_smoke_suite.py
```

## Partner review response visibility

The User Agent response exposes partner-review observability at the top level:

```text
partner_review_attempted
partner_review_mode
partner_review_service_called
live_orchestrator_configured
partner_review_status
review_services_called
partner_review_payload
partner_review
```

Expected fallback-mode example:

```json
{
  "partner_review_attempted": true,
  "partner_review_mode": "local_fallback",
  "partner_review_service_called": true,
  "live_orchestrator_configured": false,
  "review_services_called": ["partner_review_service"]
}
```

Expected live-orchestrator example:

```json
{
  "partner_review_attempted": true,
  "partner_review_mode": "live_orchestrator",
  "partner_review_service_called": true,
  "live_orchestrator_configured": true,
  "review_services_called": ["partner_review_service"]
}
```

## Partner review payload fields

The backend tries to provide these fields to partner review:

```text
request_id
origin
origin_country
destination
destination_country
selected_items or items
total_cbm
total_weight_kg
declared_value_usd
incoterm
freight_quote_usd
insurance_premium_usd
duty_rate_percent
import_tax_rate_percent
```

## Route fields

The backend fills both short and explicit country fields:

```json
{
  "origin": "partner_review_mode": "live_orchestrator",
  "partner_review_service_called": true,
  "live_orchestrator_configured": true,
  "review_services_called": ["partner_review_service"]
}
```

## Partner review payload fields

The backend tries to provide these fields to partner review:

```text
request_id
origin
origin_country
destination
destination_country
selected_items or items
total_cbm
total_weight_kg
declared_value_usd
incoterm
freight_quote_usd
insurance_premium_usd
duty_rate_percent
import_taxIndia",
  "origin_country": "India",
  "destination": "USA",
  "destination_country": "USA"
}
```

This is intentional because different partner services may expect different key names.

## Cost and trade-term fields

For text requests, the backend can parse examples like:

```text
Use CIF incoterm.
Freight quote is 1200 USD.
Insurance premium is 250 USD.
Duty rate is 5 percent.
Import tax rate is 8 percent.
```

These become:

```json
{
  "incoterm": "CIF",
  "freight_quote_usd": 1200.0,
  "insurance_premium_usd": 250.0,
  "duty_rate_percent": 5.0,
  "import_tax_rate_percent": 8.0
}
```

For JSON requests, the same fields can be passed directly.

## Live orchestrator behavior

In `app/partner_review_service.py`, if this environment variable is set:

```powershell
$env:TRADE_ORCHESTRATOR_BASE_URL = "http://127.0.0.1:8010"
```

then `run_partner_review(...)` calls the live orchestrator path.

The local `is_ready_for_partner_calls` gate applies to fallback mode, not to live orchestrator mode.

## Agents Called vs Review Services Called

`agents_called` tracks backend specialist agents, such as:

```text
shopping_agent
logistics_agent
document_ai_agent
trader_agent
```

Partner review is tracked separately through:

```text
review_services_called
partner_review
partner_review_status
specialist_responses.partner_review_service
```

Frontend should display review services separately from specialist agents.

## Current backend test coverage

Run:

```powershell
python scripts\run_backend_smoke_suite.py
```

This covers:

```text
core backend compile check
User Agent regression tests
Direct text -> Trader
Shopping/Document -> Logistics -> Trader
Document AI -> Logistics -> Trader
Partner review observability
Partner payload enrichment
Partner payload contract across text/document/JSON entry paths
Optional live partner stack check if TRADE_ORCHESTRATOR_BASE_URL is set
```

## Notes

- Trader Agent uses Gemini.
- If Gemini reasoning is unavailable, backend falls back to core Trader assessment.
- Skipping the live partner check is expected when `TRADE_ORCHESTRATOR_BASE_URL` is not set.
- A database is not required for this backend contract yet.
- Current backend is stateless orchestration plus structured handoff payloads.
