@"
# Logistics Agent Summary

## Current Version

Logistics Agent V1.1 is complete.

The logistics agent handles the cargo planning side of the shipping system. It takes shipment item data, estimates missing dimensions where possible, calculates CBM and weight, recommends containers, creates loading guidance, identifies logistics risks, and prepares handoff data for other agents.

## Main Capabilities

- Resolves item names using an item catalog.
- Estimates dimensions for common cargo items.
- Calculates unit CBM and total shipment CBM.
- Calculates total shipment weight.
- Classifies cargo into categories:
  - fragile
  - heavy
  - perishable
  - hazardous
  - radioactive
  - non-stackable
  - general cargo
- Recommends a suitable container.
- Provides container alternatives.
- Suggests container strategy, such as standard, refrigerated, hazardous, or specialist handling.
- Creates a loading sequence.
- Creates a rule-based container layout draft.
- Assesses operational logistics risk.
- Gives route and handling advice.
- Provides packaging and securing recommendations.
- Generates a shipment readiness checklist.
- Creates a handoff payload for the financial agent and future agents.

## Main Files

- app/logistics_agent.py: Main logistics planning engine.
- app/logistics_service.py: Official service interface for the logistics agent.
- app/item_resolver.py: Resolves simple item inputs using the item catalog.
- app/container_options.py: Generates container alternatives.
- app/loading_planner.py: Creates loading sequence.
- app/container_layout.py: Creates rule-based container layout draft.
- app/logistics_risk.py: Assesses operational logistics risk.
- app/route_advisor.py: Gives route and handling advice.
- app/packaging_advisor.py: Gives packaging and securing recommendations.
- app/readiness_checklist.py: Creates shipment readiness checklist.
- app/handoff_payload.py: Creates structured payload for other agents.
- data/item_catalog.json: Common cargo item catalog.
- data/scenarios/: Scenario pack for testing different shipment types.
- scripts/test_logistics_agent.py: Test script.
- scripts/run_logistics_agent.py: Runs one shipment through the logistics agent.
- scripts/run_logistics_scenarios.py: Runs all scenario files.

## How to Run Tests

```powershell
python scripts\test_logistics_agent.py