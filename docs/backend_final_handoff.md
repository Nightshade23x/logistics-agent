# Backend Integration Handoff

Branch: integration-test-trader-v5

## Current status

Backend is ready for frontend/backend integration testing.

Confirmed working:
- User Agent regression tests
- Trained router V5 routing
- Direct Trader routing
- Shopping -> Logistics -> Trader flow
- Document AI -> Logistics -> Trader flow
- Partner review observability fields
- Partner payload enrichment
- Partner payload contract across text, files, and JSON inputs
- Mock live orchestrator pipeline
- Frontend mock live partner test

## Important backend fields for frontend

Internal backend agents appear in:

agents_called

Example:
- shopping_agent
- logistics_agent
- trader_agent

Partner/orchestrator services appear in:

review_services_called

Example:
- partner_review_service

Frontend should display partner review using:
- partner_review_status
- partner_review_mode
- partner_review_service_called
- live_orchestrator_configured
- partner_review
- partner_review_payload

## Expected live mock values

With mock orchestrator enabled:
- partner_review_mode = live_orchestrator
- live_orchestrator_configured = true
- partner_review_status = review_required
- review_services_called includes partner_review_service

## Expected local fallback values

Without TRADE_ORCHESTRATOR_BASE_URL:
- partner_review_mode = local_fallback
- live_orchestrator_configured = false
- partner_review_status = partner_review_not_configured

This is expected in backend-only tests.

## Test commands

Run:
- python scripts\run_quick_backend_check.py
- python scripts\run_backend_smoke_suite.py
- python scripts\test_mock_live_orchestrator_pipeline.py

## Mock frontend test prompt

estimate freight and find supplier for 100 ceramic tiles from India to USA. Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. Duty rate is 5 percent. Import tax rate is 8 percent.

Expected payload route/cost fields:
- origin = India
- destination = USA
- incoterm = CIF
- freight_quote_usd = 1200
- insurance_premium_usd = 250
- duty_rate_percent = 5
- import_tax_rate_percent = 8

## Known non-blockers

- Gemini quota/rate-limit can make Trader LLM reasoning unavailable.
- Backend falls back to core Trader assessment.
- google.generativeai deprecation warning is non-blocking for now.
- Real orchestrator /orchestrate is blocked until Gemini quota/fallback is handled partner-side.
- _extracted_items may show percent values in frontend debug output; this is a frontend/parser display cleanup, not a backend integration blocker.

## Merge recommendation

Do not merge directly to main first.

Recommended flow:

integration-test-trader-v5
+
Avishi latest frontend branch
->
frontend-backend-final-integration
->
backend tests
->
frontend mock orchestrator test
->
real orchestrator test
->
main

Conflict rule:
- Prefer Avishi's version for frontend/UI files.
- Prefer backend integration branch for backend/router/User Agent/partner-review files.
