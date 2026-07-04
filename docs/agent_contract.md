# Finance Agent Contract

## Current state

Finance Agent uses REST, not MCP, and does not yet return the standard
`AgentResponse` envelope used by Risk/Compliance/Trader (`agent_name`,
`status`, `handoff_payload`, etc.). It returns a `FinanceReport` directly
from `/finance/report`.

This is a known inconsistency, tracked as a future improvement: wrapping
`FinanceReport` in the standard envelope so the orchestrator receives a
uniform shape from all four agents, not three-plus-one.

## Endpoints

`/finance/import-duty`, `/finance/tax`, `/finance/freight`, `/finance/insurance`,
`/finance/landed-cost`, `/finance/profit`, `/finance/currency`, `/finance/report`
(accepts optional `selling_price`), `/finance/roi`.

## Consumers

The orchestrator agent calls `/finance/report`, then overrides `import_duty`
using Trader Agent's `handoff_payload.duty_rate_percent` to keep the two
agents' numbers consistent (see orchestrator's `orchestrator_service.py`).