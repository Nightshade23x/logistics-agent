# Trader Agent Contract

## Standard response envelope

`assess_trade_plan` returns the shared multi-agent contract:

- `agent_name`: `"trader_agent"`
- `status`: `"ok" | "partial" | "error"`
- `summary`: human-readable one-paragraph result
- `plan`: steps taken (HS code classification, duty estimate, FTA check, export strategy)
- `report`: full structured findings (hs_code, duty, fta, export_strategy sub-reports)
- `input_resolution`: how input was interpreted
- `missing_information`: gaps in the assessment (e.g. unclassified HS code, no known FTA)
- `handoff_payload`: `hs_code`, `duty_rate_percent`, `fta_exists`, `agreement_name`
- `handoff_requests`: declares dependency on `finance_agent` (duty rate/HS code)
  and `risk_agent` (destination risk before finalizing strategy)

## Granular tools (non-contract, direct use)

`explain_incoterm`, `classify_hs_code`, `calculate_duty`, `check_fta`,
`suggest_export_strategy`, `plan_export` remain available for direct queries
outside the standard contract.

## Consumers

The orchestrator agent calls `assess_trade_plan` and uses `handoff_payload.duty_rate_percent`
to reconcile Finance Agent's duty calculation (see orchestrator's
`orchestrator_service.py`).