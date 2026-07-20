# Live Partner Frontend Handoff

This note is for Avishi/frontend review.

I am not editing `app/streamlit_frontend.py` from this branch because frontend is Avishi's side, and I do not want to overwrite her changes.

## Backend finding

In `app/partner_review_service.py`, live partner mode uses `TRADE_ORCHESTRATOR_BASE_URL`.

When that environment variable is set, `run_partner_review()` calls the live trade orchestrator directly:

```python
run_trade_orchestrator_review(payload, base_url=trade_orchestrator_base_url)
```

This happens before the local fallback validation gate.

So the local `is_ready_for_partner_calls` gate applies only to standalone/fallback partner mode, not to the live orchestrator path.

## Normal frontend pipeline requirement

To reach the live orchestrator from a normal frontend run, the request should have:

- Live partner mode enabled
- Correct orchestrator URL
- A request that reaches Logistics handoff
- Product/item
- Origin country
- Destination country
- Item data from Shopping or Document AI
- Logistics output such as CBM/weight when available

Good test prompt:

```text
estimate freight and find supplier for 100 ceramic tiles from India to USA
```

Fuller finance/booking test prompt:

```text
estimate freight and find supplier for 100 ceramic tiles from India to USA. Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. Duty rate is 5 percent. Import tax rate is 8 percent.
```

## UI clarification

`Agents Called` usually shows core backend agents only, such as:

- `shopping_agent`
- `logistics_agent`
- `document_ai_agent`
- `trader_agent`

Partner/orchestrator output may appear separately under:

- `review_services_called`
- `partner_review`
- `partner_review_status`
- `specialist_responses.partner_review_service`

Recommended frontend change:

Show `Review Services Called` separately from `Agents Called`.

## About cost fields

These fields are useful for finance/booking readiness:

- Incoterm
- freight quote
- insurance premium
- duty rate
- import tax rate

But they should not block the live orchestrator call when `TRADE_ORCHESTRATOR_BASE_URL` is set.

They should be shown as missing finance/booking inputs, not as blockers for invoking the live orchestrator.

## Outdated Trader warning

These frontend messages are outdated:

```text
Trader may still fail until Avishi fixes the trader agent provider setup.
Trader may still fail until Avishi fixes that agent.
```

Suggested replacement:

```text
Trader is Gemini-enabled. If Gemini reasoning is unavailable, the backend falls back to the core Trader assessment.
```

Known frontend locations from search:

- `app/streamlit_frontend.py`, around line 2545
- `app/streamlit_frontend.py`, around line 2606

## Backend status

Backend tests pass for:

- Direct text -> Trader
- Shopping -> Logistics -> Trader
- Document AI -> Logistics -> Trader
- User Agent regression tests
- Trader Gemini fallback behavior

No frontend patch is applied from this branch.
