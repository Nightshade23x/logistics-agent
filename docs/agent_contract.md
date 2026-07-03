# Multi-Agent System Contract

## Purpose

This document defines the shared structure for the multi-agent shipping and trade assistant.

The user should experience the system as one assistant. Behind the scenes, the work is divided between multiple specialist agents.

## Agents

### 1. User Agent

Role: Receptionist and coordinator.

Responsibilities:

- Talk to the customer.
- Understand the customer request.
- Decide which specialist agents are needed.
- Delegate tasks to other agents.
- Collect final responses.
- Combine all specialist outputs into one final answer.

The user should not need to see the internal agent workflow.

### 2. Shopping Agent

Role: Procurement and purchasing assistant.

Responsibilities:

- Find suppliers.
- Compare prices.
- Compare product quality.
- Suggest alternative products.
- Estimate procurement costs.

Future improvements:

- Supplier ratings.
- Supplier AI recommendations.
- Supplier reliability scoring.

### 3. Trader Agent

Role: International trade assistant.

Responsibilities:

- Assign HS codes.
- Explain Incoterms.
- Suggest export strategy.
- Calculate duties.
- Check Free Trade Agreements.

The Trader Agent should work closely with the Compliance Agent and Finance Agent.

### 4. Compliance Agent

Role: Legal and regulatory checker.

Responsibilities:

- Check allowed products.
- Check prohibited products.
- Check restricted products.
- Explain why a product is restricted.
- Identify the responsible government department.
- Identify required permits.
- Identify required licenses.
- Identify required certificates.
- Flag cargo that needs specialist approval.

Example:

For lithium batteries, the Compliance Agent may return:

- Product status: restricted.
- Required document: UN38.3 report.
- Required document: Dangerous Goods Declaration.
- Requirement: proper dangerous goods packaging.

### 5. Logistics Agent

Role: Shipping and optimization engine.

Responsibilities:

- Calculate CBM.
- Calculate shipment weight.
- Convert all units into metres, kilograms, and CBM.
- Recommend container type.
- Suggest container alternatives.
- Check physical container fit.
- Plan loading sequence.
- Suggest container layout.
- Consider fragile, heavy, perishable, hazardous, radioactive, and non-stackable cargo.
- Give packaging and securing recommendations.
- Assign cargo handling labels.
- Assess operational logistics risk.
- Give route and handling advice.
- Prepare handoff data for other agents.

Current implementation status:

- CBM calculation: implemented.
- Weight calculation: implemented.
- Unit conversion: implemented.
- Item catalog resolver: implemented.
- Fuzzy item matching: implemented.
- Direct CBM input: implemented.
- Text shipment input: implemented.
- Container recommendation: implemented.
- Container options: implemented.
- Physical container fit check: implemented.
- Input quality checking: implemented.
- Rule-based loading sequence: implemented.
- Rule-based container layout: implemented.
- Packaging and label assignment: implemented.
- Risk assessment: implemented.
- Route and handling advisor: implemented.
- Readiness checklist: implemented.
- Handoff payload: implemented.

Future improvements:

- Exact 3D bin packing.
- Dijkstra or A* route optimization.
- Vehicle routing.
- Live route, port, weather, carrier, or map API integration.
- More complete item catalog.

### 6. Finance Agent

Role: Cost and financial planning assistant.

Responsibilities:

- Estimate shipping cost.
- Estimate insurance.
- Estimate taxes.
- Estimate customs duty.
- Handle currency conversion.
- Estimate profit.
- Estimate ROI.

The Finance Agent should use data from the Logistics Agent, Trader Agent, and Compliance Agent.

Useful inputs:

- Total CBM.
- Total weight.
- Recommended container.
- Origin.
- Destination.
- Cargo risk level.
- Cargo categories.
- Route profile.

### 7. Document AI Agent

Role: Document extraction and validation assistant.

Supported documents:

- Invoice.
- Packing List.
- Bill of Lading.
- Certificate of Origin.
- Other trade documents.

Responsibilities:

- Extract products.
- Extract quantities.
- Extract weights.
- Extract country information.
- Extract supplier information.
- Detect missing documents.
- Detect incorrect or inconsistent information.
- Send extracted information to the relevant agents.

### 8. Risk Agent

Role: External risk checker.

Responsibilities:

- Check weather risk.
- Check port congestion.
- Check political instability.
- Check sanctions risk.
- Check natural disasters.
- Suggest alternate routes.
- Warn if shipment route or timing is risky.

The Risk Agent should work closely with the Logistics Agent and Compliance Agent.

## Standard Agent Response Contract

Every agent should return the same top-level structure:

agent_name: name of the agent

status: current result status

summary: short human-readable summary

plan: structured result data

report: formatted report if needed

input_resolution: explanation of assumptions, estimates, or parsed input

missing_information: list of missing details

handoff_payload: compact structured data for other agents

handoff_requests: list of other agents needed

## Recommended Status Values

Agents should use these shared statuses:

- ready_for_review
- review_required
- needs_more_information
- partial_plan_needs_more_information
- blocked
- critical_review_required
- error

Meaning:

- ready_for_review: Agent completed the task and found no major blockers.
- review_required: Agent completed the task but found warnings or risks.
- needs_more_information: Agent cannot continue without more information.
- partial_plan_needs_more_information: Agent produced a partial result but needs more data.
- blocked: Agent found a blocker that prevents progress.
- critical_review_required: Agent found a serious issue needing specialist review.
- error: Agent failed unexpectedly.

## Handoff Request Format

When one agent needs another agent, it should create a handoff request with:

- target_agent
- reason
- inputs_needed

Example:

target_agent: finance_agent

reason: Estimate freight cost, insurance cost, and shipment budget.

inputs_needed:

- total_cbm
- total_weight_kg
- recommended_container
- origin
- destination
- risk_level

## Suggested Internal Flow

Example user request:

Ship 100 scooters to Australia.

Possible internal flow:

1. User Agent receives request.
2. Compliance Agent checks if scooters are allowed or restricted.
3. Trader Agent checks HS code, Incoterms, and duties.
4. Logistics Agent calculates CBM, container, loading, and route advice.
5. Finance Agent estimates costs.
6. Risk Agent checks external route risks.
7. User Agent combines everything into one final answer.

## Agent Boundaries

User Agent should not:

- Calculate CBM itself.
- Calculate customs duty itself.
- Check regulations itself.
- Estimate route risk itself.

Logistics Agent should not:

- Make final legal compliance decisions.
- Calculate final customs duties.
- Estimate ROI.
- Validate official documents.
- Pretend to have live route or carrier data unless an API is connected.

Finance Agent should not:

- Recalculate CBM.
- Decide whether cargo is legally allowed.
- Choose loading sequence.

Compliance Agent should not:

- Estimate total shipment cost.
- Plan physical container layout.
- Choose suppliers.

## Current Project Status

The Logistics Agent is currently the most developed specialist agent.

Current Logistics Agent version: V1.2.

Implemented Logistics Agent features:

- CBM calculation.
- Weight calculation.
- Unit conversion.
- Item catalog resolution.
- Fuzzy item matching.
- Text shipment parsing.
- Direct CBM input.
- Container recommendation.
- Container alternatives.
- Physical container fit check.
- Input quality checking.
- Loading sequence planning.
- Rule-based container layout.
- Packaging and securing advice.
- Item-level cargo label assignment.
- Operational risk assessment.
- Route and handling advisor.
- Readiness checklist.
- Finance handoff payload.
- Scenario pack and tests.

Remaining future Logistics Agent improvements:

- Exact 3D bin packing.
- Real transport mode optimization.
- Dijkstra or A* route optimization.
- Vehicle routing.
- Live route, weather, port, carrier, or map API integration.
- More complete item catalog.
- Real compliance database integration through the Compliance Agent.

## Development Rule

Each agent should have:

- Main service file.
- Clear input format.
- Clear output format.
- Tests.
- Sample data or scenarios.
- Handoff payload.
- Documentation.

## Branching Rule

Feature work should happen on separate branches.

Recommended branches:

- logistics
- finance
- compliance
- shopping
- trader
- documents
- risk
- user-agent
- agent-contract

The main branch should contain stable, reviewed work only.
