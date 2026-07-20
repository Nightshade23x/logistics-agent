# Integration merge readiness note

Current branch: `integration-test-trader-v5`

## Backend status

The backend integration branch is ready for frontend/backend review.

Confirmed working:

- User Agent regression tests pass.
- Trained router V5 works for Shopping, Document AI, Logistics, and unknown routing.
- Direct Trader routing works through deterministic guardrail.
- Shopping -> Logistics -> Trader integration works.
- Document AI -> Logistics -> Trader integration works.
- Partner review payload enrichment works.
- Partner review observability fields are exposed at top level.
- Partner payload contract passes across:
  - text entry path
  - document/file entry path
  - JSON entry path
- Mock live orchestrator pipeline passes through the normal User Agent flow.
- Frontend partner review sample export is available.

## Important frontend display rule

`agents_called` shows internal backend agents only, for example:

```json
["shopping_agent", "logistics_agent"]
```

External partner/orchestrator review should be shown using:

```json
"review_services_called": ["partner_review_service"]
```

The frontend should also display:

```text
partner_review_status
partner_review_mode
partner_review_attempted
partner_review_service_called
live_orchestrator_configured
partner_review
partner_review_payload
```

## Live orchestrator status

The real live orchestrator service was tested locally.

Confirmed:

- Orchestrator service starts.
- `/health` works.
- Backend can reach the orchestrator URL.

Current blocker:

The real `/orchestrate` call can fail with HTTP 500 because the orchestrator Gemini provider hit quota:

```text
ResourceExhausted 429
generate_content_free_tier_requests
limit: 20
model: gemini-2.5-flash
```

This is not a Samar backend routing issue. The request reaches the orchestrator, then the orchestrator crashes internally when Gemini quota is exceeded.

Recommended partner-side fix:

The orchestrator should catch Gemini quota/rate-limit/provider errors and return a structured partner-review response instead of HTTP 500.

## Useful commands

Quick backend check:

```powershell
python scripts\run_quick_backend_check.py
```

Full backend smoke suite:

```powershell
python scripts\run_backend_smoke_suite.py
```

Mock live orchestrator pipeline:

```powershell
python scripts\test_mock_live_orchestrator_pipeline.py
```

Frontend partner review sample:

```powershell
python scripts\export_frontend_partner_review_sample.py
```

Real live orchestrator check, only when Finance + Orchestrator are running and Gemini quota is available:

```powershell
$env:TRADE_ORCHESTRATOR_BASE_URL = "http://127.0.0.1:8010"
python scripts\check_live_partner_stack.py
python scripts\test_live_orchestrator_pipeline.py
```

## Merge recommendation

This branch is suitable for frontend/backend integration review.

Before final merge, frontend should confirm that partner review fields are displayed separately from internal agents.
