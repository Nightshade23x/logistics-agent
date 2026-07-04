# Multi-Agent System Integration Plan

## Purpose

This document explains how the different trade, shopping, document, and logistics agents will work together.

The goal is to connect the specialist agents into one coordinated workflow without mixing their responsibilities.

## Current Agent Branches

The current specialist agents are being developed separately:

- logistics branch:
  - Logistics Agent V1.3
  - Handles shipment planning, CBM, weight, packaging, container advice, FCL/LCL recommendation, and logistics handoff.

- document-agent branch:
  - Document AI Agent V1.3
  - Handles trade/shipping document extraction, document validation, invoice vs packing list checks, document set completeness, and document routing.

- shopping-agent branch:
  - Shopping Agent V1.5
  - Handles supplier matching, supplier preferences, budget checks, natural language shopping requests, supplier risk scoring, purchase order drafts, and supplier shortlist export.

The shared agent contract is in:

- docs/agent_contract.md

## Frontend vs User Agent

The frontend and User Agent are different.

### Frontend

The frontend is the user interface.

Examples:

- Streamlit app
- web app
- chat interface
- upload form
- dashboard

The frontend collects user input and displays the final answer.

### User Agent

The User Agent is the orchestrator behind the interface.

It does not replace the frontend.

The User Agent is responsible for:

- understanding the user's request
- deciding which specialist agent should run
- checking what information is missing
- asking the user follow-up questions
- sending the correct handoff payloads to other agents
- combining outputs from multiple agents into one final answer
- preventing agents from doing work outside their role

## High-Level Flow

Basic system flow:

User
↓
Frontend / UI
↓
User Agent
↓
Specialist Agents
↓
User Agent
↓
Frontend / UI
↓
User

The User Agent coordinates the work. The frontend only displays and collects information.

## Specialist Agent Roles

### Shopping Agent

The Shopping Agent handles supplier and procurement planning.

It should answer questions like:

- What supplier should I use?
- Which supplier is cheapest?
- Which supplier is best quality?
- Which suppliers fit my budget?
- Can I avoid certain supplier countries?
- Can I generate draft purchase orders?

Shopping Agent produces handoff data for:

- Finance Agent
- Trader Agent
- Compliance Agent
- User Agent

Shopping Agent should not calculate shipping/container loading. That belongs to Logistics Agent.

### Document AI Agent

The Document AI Agent handles document extraction and document validation.

It should answer questions like:

- What is in this invoice?
- Does the invoice match the packing list?
- Are required documents missing?
- What shipment data can be extracted from documents?

Document AI Agent produces handoff data for:

- Logistics Agent
- Finance Agent
- Compliance Agent
- User Agent

Document AI Agent should not choose suppliers or calculate final shipping plans.

### Logistics Agent

The Logistics Agent handles shipping and cargo planning.

It should answer questions like:

- What is the shipment CBM?
- What is the total weight?
- Is this LCL or FCL?
- Which container type is suitable?
- What packaging and loading advice is needed?
- What logistics risks exist?

Logistics Agent produces handoff data for:

- Finance Agent
- Compliance Agent
- Risk Agent
- User Agent

Logistics Agent should not select suppliers or calculate profit.

### Finance Agent

The Finance Agent should handle cost and financial analysis.

Expected future responsibilities:

- landed cost
- procurement cost
- freight estimate
- insurance estimate
- taxes and duties
- profit
- ROI
- budget check

Finance Agent should use handoff payloads from Shopping, Logistics, Document AI, Trader, and Compliance.

### Trader Agent

The Trader Agent should handle trade strategy.

Expected future responsibilities:

- HS code suggestions
- Incoterms
- trade route logic
- import/export strategy
- duty-related trade planning
- supplier country trade considerations

### Compliance Agent

The Compliance Agent should handle rules, restrictions, and documentation checks.

Expected future responsibilities:

- required certificates
- restricted products
- import/export document requirements
- country-specific compliance checks
- product category warnings

### Risk Agent

The Risk Agent should handle cross-system risk.

Expected future responsibilities:

- supplier risk
- route risk
- cargo risk
- document risk
- compliance risk
- financial risk
- final overall risk summary

## Shared Agent Response Contract

Each agent should return the same broad response structure:

```python
{
    "agent_name": "...",
    "status": "...",
    "summary": "...",
    "plan": {...},
    "report": "...",
    "input_resolution": {...},
    "missing_information": [...],
    "handoff_payload": {...},
    "handoff_requests": [...]
}
