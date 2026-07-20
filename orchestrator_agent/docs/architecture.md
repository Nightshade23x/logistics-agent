# Two-Coordinator Architecture

This system has two independent orchestrators, not one:

## Orchestrator Agent (this branch) -- trade, compliance, finance, risk

Answers: "Can I legally ship this, what will it cost, and what could go wrong?"

Coordinates: `risk_agent`, `compliance_agent`, `trader_agent` (MCP),
`finance_agent` (REST). Exposes `POST /orchestrate` -- accepts free-text
shipment queries, parses them via LLM, calls all four agents, reconciles
Trader/Finance duty figures, derives a rule-based verdict
(clear/review_required/blocked), and synthesizes one prioritized answer.

## User Agent (Samar's branches) -- physical shipping, procurement, documents

Answers: "Will it fit, where do I source it, are the documents in order?"

Coordinates: `logistics_agent`, `shopping_agent`, `document_agent`.

## Integration boundary (not yet built)

The two coordinators do not currently call each other. Known future work:
- Bridge between this orchestrator and Samar's user-agent
- Logistics handoff payload (CBM, weight, container data) is not currently
  fed into this orchestrator's finance/risk calls
- Status vocabulary differs (`ok/partial/error` here vs Samar's
  `ready_for_review/review_required/blocked` -- worth aligning before a
  shared AI interface consumes both halves)

## Running this half of the stack

1. Start Finance Agent: `uvicorn finance_agent.finance_agent.api:app --port 8003`
   (from the `agent-finance` worktree)
2. Ensure `risk_agent`, `compliance_agent`, `trader_agent` worktrees have their
   own venvs installed (see `mcp_client.py` for expected paths via
   `RISK_AGENT_DIR`, `COMPLIANCE_AGENT_DIR`, `TRADER_AGENT_DIR` env vars)
3. Start this orchestrator: `uvicorn orchestrator_agent.api:app --port 8010`
   (from the `orchestrator_agent` folder)
4. `POST /orchestrate` with `{"query": "..."}`