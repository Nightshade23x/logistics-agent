# Logistics Agent Demo Runbook

## Current Demo Status

The backend can run in two modes:

1. **Standalone backend mode**
   - Does not require partner services.
   - Shopping Agent works.
   - Logistics Agent works.
   - Partner Review Service runs but reports `partner_review_not_configured`.
   - Compact frontend payload is still valid.
   - Backend contract validation passes.

2. **Live partner mode**
   - Requires Avishi's orchestrator on port `8010`.
   - Requires Finance Agent on port `8003`.
   - Backend can call the Trade Orchestrator successfully.
   - Risk Agent works.
   - Compliance Agent works.
   - Finance Agent works.
   - Trader Agent is currently blocked externally because it requires `OPENAI_API_KEY`.

## Main Architecture

```text
User / Gemini UI
    -> Samar User Agent backend
        -> Shopping Agent
        -> Logistics Agent
        -> Document AI Agent, when documents are provided
        -> Partner Review Service
            -> Avishi Trade Orchestrator
                -> Risk Agent
                -> Compliance Agent
                -> Trader Agent
                -> Finance Agent
