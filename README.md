# Logistics Agent Backend

This project is a modular AI-based logistics and procurement backend. It accepts shopping, shipment, text, and document inputs, then routes them through specialist agents for procurement review, logistics planning, document validation, partner review preparation, and frontend-ready payload generation.

The current backend is demo-ready in standalone mode. It also supports live partner orchestration when the external partner services are running.

---

## Current Status

| Area | Status |
|---|---|
| User Agent / Router | Working |
| Shopping Agent | Working |
| Logistics Agent | Working |
| Document AI Agent | Working |
| Logistics Visualizer Payload | Working |
| Partner Review Service | Working |
| Trade Orchestrator Adapter | Working |
| Compact Frontend Payload | Working |
| Backend Payload Validation | Working |
| Standalone Demo Mode | Working |
| Live Partner Mode | Partially working; waiting on partner Trader Agent setup |

---

## What The Backend Does

The backend can:

1. Process shopping/procurement requests.
2. Select suppliers from a supplier catalog.
3. Estimate procurement cost.
4. Calculate shipment CBM and weight.
5. Recommend container options.
6. Identify cargo risk such as fragile, heavy, hazardous, perishable, or non-stackable cargo.
7. Generate packaging, handling, loading, and route advice.
8. Produce a logistics visualizer payload for frontend container/cargo rendering.
9. Parse and validate shipping documents such as invoice, packing list, bill of lading, and certificate of origin.
10. Prepare partner review payloads for Risk, Compliance, Trader, and Finance checks.
11. Call a live external Trade Orchestrator when configured.
12. Degrade safely when partner services are offline.
13. Return structured frontend-ready payloads.

---

## Main Architecture

```text
User / Gemini / Frontend
    -> User Agent backend
        -> Shopping Agent
        -> Logistics Agent
        -> Document AI Agent
        -> Partner Review Service
            -> Trade Orchestrator Adapter
                -> External Risk Agent
                -> External Compliance Agent
                -> External Trader Agent
                -> External Finance Agent
```

---

## Main Demo Command

Run this before any demo:

```powershell
cd C:\Users\Samar\Desktop\logistics-agent
.\.venv\Scripts\Activate.ps1

python scripts\run_all_demo_checks.py
```

Expected result:

```text
ALL DEMO CHECKS PASSED
```

This verifies the standalone backend demo path, frontend payloads, shopping, logistics, documents, visualizer, text quality, adapter behavior, and repo hygiene.

---

## Export Final Demo Bundle

To generate the complete demo evidence bundle:

```powershell
python scripts\export_final_demo_bundle.py
```

Output folder:

```text
demo_outputs/final_demo_bundle
```

This bundle includes:

```text
checks/all_demo_checks.txt
shopping_demo/frontend_payload_compact.json
shopping_demo/frontend_payload_shopping.json
shopping_demo/backend_status.json
shopping_demo/demo_report.md
shopping_demo/demo_index.md
logistics/logistics_scenario_pack.txt
logistics/oversized_logistics_report.txt
documents/document_agent_report.txt
documents/document_pair_validation_report.txt
documents/document_set_completeness_report.txt
partner/live_partner_stack_check.txt
docs/demo_runbook.md
docs/frontend_payload_contract.md
docs/backend_agent_status_report.md
```

---

## Standalone Mode

Standalone mode does not require external partner services.

Run:

```powershell
Remove-Item Env:\TRADE_ORCHESTRATOR_BASE_URL -ErrorAction SilentlyContinue

python scripts\run_demo_standalone_check.py
```

Expected high-level result:

```text
Partner review status: partner_review_not_configured
Contract valid: True
RESULT: PASS
```

This proves the backend still returns a valid frontend payload even when partner services are not connected.

---

## Live Partner Mode

Live partner mode requires the external partner stack.

Finance Agent:

```powershell
cd C:\Users\Samar\Desktop\logistics-finance
.\.venv\Scripts\python.exe -m uvicorn finance_agent.finance_agent.api:app --port 8003
```

Trade Orchestrator:

```powershell
cd C:\Users\Samar\Desktop\logistics-orchestrator\orchestrator_agent
powershell -ExecutionPolicy Bypass -File .\start_orchestrator_local.ps1
```

Backend test:

```powershell
cd C:\Users\Samar\Desktop\logistics-agent
.\.venv\Scripts\Activate.ps1

$env:TRADE_ORCHESTRATOR_BASE_URL = "http://127.0.0.1:8010"

python scripts\run_frontend_payload.py json data\suppliers\sample_shopping_request.json --raw
```

Optional live partner checker:

```powershell
python scripts\check_live_partner_stack.py
```

---

## Current Partner Limitation

The backend partner adapter is working.

The current external blocker is the partner Trader Agent:

```text
trader_agent uses OpenAI(api_key=os.environ["OPENAI_API_KEY"])
trader_agent requires OPENAI_API_KEY
trader_agent requirements.txt was missing openai
```

This is partner-side setup, not backend-side logic.

The backend can still run in standalone mode and can call the orchestrator when it is available.

---

## Key Scripts

| Script | Purpose |
|---|---|
| `scripts/run_all_demo_checks.py` | Runs the full standalone demo regression suite. |
| `scripts/run_demo_standalone_check.py` | Checks standalone backend mode. |
| `scripts/export_final_demo_bundle.py` | Exports final demo evidence bundle. |
| `scripts/export_demo_pack.py` | Exports shopping/frontend demo payloads. |
| `scripts/check_live_partner_stack.py` | Checks optional live partner services. |
| `scripts/demo_user_agent_summary.py` | Shows end-to-end user agent demo flows. |
| `scripts/run_compact_frontend_payload.py` | Generates compact frontend payload. |
| `scripts/run_frontend_payload.py` | Generates full frontend payload. |
| `scripts/run_logistics_scenarios.py` | Runs logistics scenario pack. |
| `scripts/run_logistics_plan.py` | Runs detailed logistics report for one scenario. |
| `scripts/run_document_agent.py` | Runs sample Document AI extraction. |
| `scripts/run_document_pair_agent.py` | Runs invoice vs packing list validation. |
| `scripts/run_document_set_agent.py` | Runs document set completeness check. |

---

## Test Coverage

The demo check currently covers:

```text
Trade orchestrator adapter tests
Frontend payload tests
Compact frontend payload tests
Logistics visualizer payload test
Payload text quality test
Repo hygiene check
End-to-end user agent demo test
Shopping demo regression test
Document demo regression test
Logistics scenario regression test
Logistics report text quality test
Standalone demo check
```

Run all:

```powershell
python scripts\run_all_demo_checks.py
```

---

## Shopping Agent

The Shopping Agent can:

```text
select supplier options
estimate procurement cost
calculate supplier risk
produce procurement guidance
prepare selected items for logistics handoff
```

Sample request:

```text
data/suppliers/sample_shopping_request.json
```

Key tests:

```powershell
python scripts/test_shopping_agent.py
python scripts/test_shopping_quality_review.py
python scripts/test_procurement_advisor.py
python scripts/test_shopping_demo_regression.py
```

---

## Logistics Agent

The Logistics Agent can:

```text
calculate CBM
calculate total weight
recommend containers
compare container options
check physical fit
classify cargo categories
produce loading sequence
produce packaging advice
produce route and handling advice
produce readiness checklist
```

Scenario coverage:

| Scenario | Expected Status |
|---|---|
| `normal_dry_cargo.json` | `ready_for_review` |
| `hazardous_cargo.json` | `critical_review_required` |
| `oversized_multi_container.json` | `critical_review_required` |
| `perishable_cargo.json` | `review_required` |
| `unknown_item_missing_dimensions.json` | `partial_plan_needs_more_information` |

Run:

```powershell
python scripts/run_logistics_scenarios.py
python scripts/run_logistics_plan.py data/scenarios/oversized_multi_container.json
```

---

## Logistics Visualizer

The backend returns a frontend-ready `logistics_visualizer` object.

It includes:

```text
container
cargo_mix
container_options
zone_layout
loading_sequence
fit_check
layout_notes
frontend_hints
```

This means the frontend does not need to parse raw text to create a container/cargo visualization.

---

## Document AI Agent

Document AI can process:

```text
invoice
packing list
bill of lading
certificate of origin
```

It can:

```text
extract document fields
extract shipment items
validate document quality
compare invoice vs packing list
check document set completeness
prepare handoff requests for logistics, finance, and compliance
```

Run:

```powershell
python scripts/run_document_agent.py
python scripts/run_document_pair_agent.py
python scripts/run_document_set_agent.py
```

Key tests:

```powershell
python scripts/test_document_agent.py
python scripts/test_document_quality_review.py
python scripts/test_document_requirements_advisor.py
python scripts/test_trade_compliance_readiness_advisor.py
python scripts/test_document_demo_regression.py
```

---

## Frontend Payloads

The backend supports:

```text
frontend_payload
compact_frontend_payload
```

For frontend or Gemini UI work, use:

```powershell
python scripts/run_compact_frontend_payload.py json data/suppliers/sample_shopping_request.json
```

Important fields:

```text
executive_summary
ui_sections
booking_readiness
final_answer
action_plan
logistics_metrics
logistics_visualizer
partner_review_status
backend_validation
request_metadata
```

See:

```text
docs/frontend_payload_contract.md
```

---

## Important Documentation

| Document | Purpose |
|---|---|
| `docs/demo_runbook.md` | How to run standalone and live partner demos. |
| `docs/frontend_payload_contract.md` | Payload contract for frontend/Gemini integration. |
| `docs/backend_agent_status_report.md` | Current backend and agent readiness report. |
| `docs/backend_architecture.md` | Backend architecture notes. |
| `docs/partner_integration_reference.md` | Partner integration reference. |
| `docs/logistics_agent_summary.md` | Logistics agent summary. |
| `docs/shopping_agent_summary.md` | Shopping agent summary. |
| `docs/document_ai_agent_summary.md` | Document AI summary. |

---

## Files That Should Not Be Committed

Do not commit:

```text
.venv/
__pycache__/
*.pyc
demo_outputs/
.env
.env.local
local_secrets.ps1
start_orchestrator_local.ps1
raw handoff zip files unless intentionally required
API keys
```

The repo hygiene check helps detect accidental tracked secrets or generated files:

```powershell
python scripts/test_repo_hygiene.py
```

---

## Current Backend Readiness

| Area | Readiness |
|---|---|
| Standalone backend demo | Ready |
| Shopping Agent | Ready |
| Logistics Agent | Ready |
| Document AI Agent | Ready |
| Logistics Visualizer | Ready |
| Frontend payload contract | Ready |
| Partner adapter | Ready |
| Final demo bundle exporter | Ready |
| Live full partner demo | Waiting on partner Trader Agent fix |

---

## Recommended Demo Flow

1. Run all checks:

```powershell
python scripts/run_all_demo_checks.py
```

2. Export final demo bundle:

```powershell
python scripts/export_final_demo_bundle.py
```

3. Show compact frontend payload:

```powershell
python scripts/run_compact_frontend_payload.py json data/suppliers/sample_shopping_request.json
```

4. Show logistics scenarios:

```powershell
python scripts/run_logistics_scenarios.py
```

5. Show document workflow:

```powershell
python scripts/run_document_set_agent.py
```

6. Explain partner status:

```text
Backend integration is working.
Risk, Compliance, and Finance worked when partner stack was running.
Trader Agent is waiting on partner-side OpenAI setup.
Standalone demo is not blocked.
```

---

## Summary

The backend is ready for standalone demonstration.

It supports shopping, logistics, document AI, partner review preparation, frontend payloads, visualizer data, demo exports, and regression checks.

The only current external blocker is the live partner Trader Agent setup.
