# Frontend Payload Contract

## Purpose

This document explains the backend payload that the frontend or Gemini interface can use to render the Logistics Agent result.

The backend supports two main frontend payload formats:

1. `frontend_payload`
2. `compact_frontend_payload`

For demo and UI work, use the compact payload unless raw debugging is needed.

---

## Generate Compact Payload

```powershell
cd C:\Users\Samar\Desktop\logistics-agent
.\.venv\Scripts\Activate.ps1

python scripts\run_compact_frontend_payload.py json data\suppliers\sample_shopping_request.json
```

---

## Top-Level Compact Payload Shape

```json
{
  "payload_type": "compact_frontend_payload",
  "agent_name": "user_agent",
  "status": "review_required",
  "decision": "review_required",
  "detected_intent": "shopping",
  "agents_called": [],
  "short_answer": "",
  "executive_summary": {},
  "ui_sections": [],
  "booking_readiness": {},
  "final_answer": {},
  "action_plan": {},
  "logistics_metrics": {},
  "logistics_visualizer": {},
  "partner_review_status": "",
  "partner_review_summary": "",
  "backend_validation": {},
  "request_metadata": {},
  "debug_counts": {}
}
```

---

## 1. Executive Summary

Use `executive_summary` for the main top card in the UI.

Example:

```json
{
  "status": "needs_more_information",
  "headline": "Shipment is usable for first-pass planning, but not ready to book yet.",
  "decision": "review_required",
  "ready_for_first_pass": true,
  "ready_for_booking": false,
  "booking_score": 40,
  "next_gate": "fill_missing_information"
}
```

Recommended frontend rendering:

- Show the headline as the main result.
- Show `decision` as a badge.
- Show `booking_score` as a score or progress indicator.
- Show `ready_for_first_pass` and `ready_for_booking` as clear yes/no indicators.

---

## 2. UI Sections

Use `ui_sections` to render the main result cards.

Current sections usually include:

```text
Executive Decision
Shipment Snapshot
Procurement
Logistics
Compliance & Documents
Costs & Insurance
Partner Checks
Next Actions
```

Each section follows this shape:

```json
{
  "section_id": "logistics",
  "title": "Logistics",
  "status": "review_required",
  "summary": "Logistics plan is usable for first-pass planning but needs review before booking.",
  "metrics": {},
  "bullets": [],
  "actions": []
}
```

Recommended frontend rendering:

- Render each section as a card.
- Show `status` as a badge.
- Show `metrics` in a compact grid.
- Show `bullets` as notes or warnings.
- Show `actions` as recommended next steps.

---

## 3. Logistics Metrics

Use `logistics_metrics` for quick shipment stats.

Example:

```json
{
  "total_cbm": 19.41,
  "total_weight_kg": 2250.0,
  "recommended_container": "20ft Standard Container",
  "recommended_load_type": "fcl_preferred",
  "risk_level": "high",
  "risk_score": 6,
  "readiness_status": "ready_for_review_with_high_risk"
}
```

Recommended frontend rendering:

- Total CBM
- Total weight
- Recommended container
- Recommended load type
- Risk level
- Risk score

---

## 4. Logistics Visualizer

Use `logistics_visualizer` for a container/cargo visualizer.

Top-level shape:

```json
{
  "visualizer_type": "container_load_visualizer",
  "status": "available",
  "container": {},
  "cargo_mix": [],
  "container_options": [],
  "zone_layout": [],
  "loading_sequence": [],
  "fit_check": {},
  "layout_notes": [],
  "frontend_hints": {}
}
```

This field is designed so the frontend does not need to parse raw text. It can directly render a visual logistics view.

---

## 4.1 Container

Example:

```json
{
  "selected_container": "20ft Standard Container",
  "recommended_load_type": "fcl_preferred",
  "total_cbm": 19.41,
  "total_weight_kg": 2250.0,
  "total_items": 155,
  "capacity_cbm": 33.2,
  "safe_capacity_cbm": 28.22,
  "max_payload_kg": 28200,
  "utilization_percent": 58.46,
  "risk_level": "high",
  "risk_score": 6
}
```

Recommended frontend rendering:

- Selected container label
- Utilization progress bar
- Total CBM
- Total weight
- Safe capacity
- Payload limit
- Risk badge

---

## 4.2 Cargo Mix

Example:

```json
[
  {
    "item_name": "TVs",
    "quantity": 50,
    "dimensions_m": {
      "length": 1.2,
      "width": 0.2,
      "height": 0.8
    },
    "unit_cbm": 0.19,
    "total_cbm": 9.6,
    "unit_weight_kg": 12.0,
    "total_weight_kg": 600.0,
    "stackable": false,
    "unload_priority": 2,
    "category_tags": ["fragile", "non_stackable"]
  }
]
```

Recommended frontend rendering:

- Cargo item cards or table
- Quantity
- Dimensions
- CBM
- Weight
- Category tags such as fragile, heavy, hazardous, perishable, non-stackable

---

## 4.3 Container Options

Example:

```json
[
  {
    "option_name": "20ft Standard Container",
    "container_count": 1,
    "total_capacity_cbm": 33.2,
    "safe_capacity_cbm": 28.22,
    "payload_limit_kg": 28200,
    "estimated_utilization_percent": 58.46,
    "unused_safe_cbm": 8.81,
    "reason": "Fits within safe CBM and payload limits."
  }
]
```

Recommended frontend rendering:

- Show alternative container options.
- Highlight the selected/recommended option.
- Show utilization and unused safe CBM.
- Use this for comparing 20ft, 40ft, high cube, and multi-container options.

---

## 4.4 Zone Layout

Example:

```json
[
  {
    "zone_name": "front_floor_base_zone",
    "description": "Front/base floor area for heavy cargo and stable weight distribution.",
    "items": [
      {
        "item_name": "Scooters",
        "quantity": 5,
        "sequence_number": 1,
        "reason": "heavy cargo should support the load from the bottom; non-stackable cargo should not have items placed above it."
      }
    ]
  }
]
```

Recommended frontend rendering:

- Simple container map.
- Group items by zone.
- Show zone descriptions.
- Show item chips/cards inside each zone.

---

## 4.5 Loading Sequence

Example:

```json
[
  {
    "sequence_number": 1,
    "item_name": "Scooters",
    "quantity": 5,
    "suggested_zone": "Bottom floor zone, evenly distributed and secured",
    "category_tags": ["heavy", "non_stackable"],
    "reason": "heavy cargo should support the load from the bottom; non-stackable cargo should not have items placed above it."
  }
]
```

Recommended frontend rendering:

- Numbered loading timeline.
- Show item name and quantity.
- Show suggested zone.
- Show the reason for each loading step.

---

## 4.6 Fit Check

Example:

```json
{
  "status": "fits_selected_container",
  "selected_container_checked": "20ft Standard Container",
  "warnings": ["No major physical container fit issues detected."],
  "recommendations": ["Cargo appears physically suitable for standard container loading."],
  "item_fit_results": []
}
```

Recommended frontend rendering:

- Fit status badge.
- Warning list.
- Recommendation list.
- Optional item-level fit table.

---

## 4.7 Frontend Hints

Example:

```json
{
  "primary_view": "container_utilization",
  "secondary_view": "zone_layout",
  "show_cargo_tags": true,
  "show_fit_warnings": true,
  "show_loading_sequence": true
}
```

Recommended frontend rendering:

- Use `primary_view` as the default selected tab.
- Use `secondary_view` as the second visual panel.
- Use the boolean flags to decide which UI blocks to show.

---

## 5. Booking Readiness

Use `booking_readiness` to show whether the shipment can move from planning to booking.

Example:

```json
{
  "status": "needs_more_information",
  "score": 40,
  "ready_for_first_pass": true,
  "ready_for_booking": false,
  "next_gate": "fill_missing_information",
  "blockers": [],
  "missing_information": [],
  "review_items": [],
  "ready_items": [],
  "next_steps": []
}
```

Recommended frontend rendering:

- Readiness score
- Ready for first pass
- Ready for booking
- Missing information
- Review items
- Next steps

---

## 6. Final Answer

Use `final_answer` for a user-readable result summary.

Example:

```json
{
  "status": "review_required",
  "headline": "This request is usable for first-pass planning, but review is still required.",
  "answer_text": "This request is usable for first-pass planning, but review is still required.",
  "ready_items": [],
  "blockers": [],
  "warnings": [],
  "next_actions": []
}
```

Recommended frontend rendering:

- Main headline
- Answer text
- Warnings
- Blockers
- Next actions

---

## 7. Action Plan

Use `action_plan` for operational next steps.

Example:

```json
{
  "status": "review_before_booking",
  "summary": "The plan is usable for first-pass planning, but review is needed before booking.",
  "immediate_actions": [],
  "before_booking": [],
  "partner_steps": [],
  "user_questions": [],
  "ready_to_continue": []
}
```

Recommended frontend rendering:

- Immediate actions
- Before booking tasks
- Partner steps
- User questions
- Ready-to-continue items

---

## 8. Partner Review Status

When partner services are offline:

```json
{
  "partner_review_status": "partner_review_not_configured"
}
```

When the live orchestrator is connected:

```json
{
  "partner_review_status": "review_required"
}
```

Recommended frontend rendering:

- Show partner status as a badge.
- If `partner_review_not_configured`, display it as external partner checks not connected.
- If live orchestrator is connected, show risk/compliance/trader/finance results where available.

---

## 9. Backend Validation

Always check `backend_validation` before treating the payload as final.

Example:

```json
{
  "response_contract_valid": true,
  "response_contract_errors": [],
  "response_contract_warnings": []
}
```

Recommended frontend rendering:

- If `response_contract_valid` is true, render normally.
- If false, show a backend payload warning.
- In demo mode, this should be true.

---

## 10. Request Metadata

Example:

```json
{
  "request_type": "json_file",
  "input_source": "data\\suppliers\\sample_shopping_request.json",
  "include_raw_response": false,
  "served_by": "backend_service"
}
```

Recommended frontend rendering:

- Useful for debugging.
- Usually not needed in the main user-facing UI.

---

## Recommended Frontend Render Order

```text
1. executive_summary
2. logistics_metrics
3. logistics_visualizer
4. ui_sections
5. booking_readiness
6. final_answer
7. action_plan
8. partner_review_status
9. backend_validation
```

---

## Demo Commands

Run all standalone checks before demo:

```powershell
cd C:\Users\Samar\Desktop\logistics-agent
.\.venv\Scripts\Activate.ps1

python scripts\run_all_demo_checks.py
```

Expected result:

```text
ALL DEMO CHECKS PASSED
```

Generate compact frontend payload:

```powershell
python scripts\run_compact_frontend_payload.py json data\suppliers\sample_shopping_request.json
```

Save compact frontend payload:

```powershell
New-Item -ItemType Directory -Force demo_outputs | Out-Null

python scripts\run_compact_frontend_payload.py json data\suppliers\sample_shopping_request.json |
  Set-Content demo_outputs\standalone_compact_payload.json -Encoding UTF8
```

---

## Standalone Mode

Standalone mode means the partner orchestrator is not connected.

Expected result:

```json
{
  "partner_review_status": "partner_review_not_configured",
  "backend_validation": {
    "response_contract_valid": true
  }
}
```

This proves the backend can still produce a valid frontend payload without external partner services.

---

## Live Partner Mode

Live partner mode requires Avishi's orchestrator and Finance Agent to be running.

Finance Agent:

```powershell
cd C:\Users\Samar\Desktop\logistics-finance
.\.venv\Scripts\python.exe -m uvicorn finance_agent.finance_agent.api:app --port 8003
```

Orchestrator:

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

Expected high-level result:

```text
backend calls trade_orchestrator
risk_agent works
compliance_agent works
finance_agent works
trader_agent depends on partner OpenAI setup
backend_validation.response_contract_valid is true
```

---

## Current Partner Limitation

The backend integration is working.

The current external limitation is the partner Trader Agent setup:

```text
trader_agent uses OpenAI(api_key=os.environ["OPENAI_API_KEY"])
trader_agent requires OPENAI_API_KEY
trader_agent requirements.txt was missing openai
```

This is not a backend blocker. The backend can run in standalone mode and can call the orchestrator when it is available.

---

## Frontend Rule

The frontend should not rely on raw text only.

Use structured fields first:

```text
executive_summary
logistics_metrics
logistics_visualizer
ui_sections
booking_readiness
final_answer
action_plan
partner_review_status
backend_validation
```

Raw response should only be used for debugging.
