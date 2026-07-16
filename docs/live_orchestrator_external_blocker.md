# Live orchestrator external blocker note

The backend live partner path has been tested against a running local orchestrator service.

Confirmed working:

- Orchestrator service starts.
- `/health` returns OK.
- Backend can reach the orchestrator URL.
- Mock live orchestrator pipeline passes through the normal User Agent flow.

Current external blocker:

The real `/orchestrate` call can fail with HTTP 500 when the orchestrator's Gemini provider hits quota.

Observed error:

```text
ResourceExhausted 429
generate_content_free_tier_requests
limit: 20
model: gemini-2.5-flash
```

Interpretation:

This is not a trained-router issue and not a Samar backend routing issue. It means the live orchestrator received the request but crashed internally when Gemini rejected the generation request.

Recommended partner-side fix:

The orchestrator should catch Gemini quota/rate-limit/provider errors and return a structured partner-review response instead of HTTP 500, for example:

```json
{
  "status": "review_required",
  "summary": "Live LLM reasoning unavailable because provider quota was exceeded.",
  "blockers": [],
  "warnings": ["Gemini quota exceeded; fallback review used."],
  "recommendations": ["Retry later or configure a paid/higher-quota Gemini key."]
}
```

Useful local commands:

```powershell
python scripts\run_quick_backend_check.py
python scripts\run_backend_smoke_suite.py
python scripts\test_mock_live_orchestrator_pipeline.py

$env:TRADE_ORCHESTRATOR_BASE_URL = "http://127.0.0.1:8010"
python scripts\check_live_partner_stack.py
python scripts\test_live_orchestrator_pipeline.py
```
