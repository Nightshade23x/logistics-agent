# Logistics Agent V1

This branch contains the first version of the logistics planning engine.

## Current Features

- Calculates CBM for cargo items.
- Calculates total shipment CBM.
- Calculates total shipment weight.
- Classifies cargo into categories such as:
  - fragile
  - heavy
  - perishable
  - hazardous
  - radioactive
  - non-stackable
  - general cargo
- Recommends a container based on CBM and weight.
- Generates basic loading advice.

## Current Scope

This is not yet using an LLM. The first version is rule-based so that the core calculations are reliable. Later, the logistics agent can call these functions as tools.

## Next Steps

- Add richer item examples.
- Add better loading rules.
- Add support for origin and destination.
- Connect this logistics engine to the main multi-agent system.
- Later connect to an LLM and visualization tool.

## V1 Completion Additions

The logistics agent now also includes:

- Packaging and securing recommendations.
- Item-level packaging actions.
- Recommended labels and materials.
- Shipment readiness checklist.
- Before-booking, before-loading, and before-dispatch checks.
- Handoff checks for finance and compliance agents.

With these additions, Logistics Agent V1 is ready for integration with the future multi-agent system.
