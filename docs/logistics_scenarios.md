# Logistics Scenario Pack

This folder contains sample shipments used to test the Logistics Agent across different cargo situations.

## Scenarios

- normal_dry_cargo.json: Standard dry cargo with no special handling.
- perishable_cargo.json: Temperature-sensitive cargo that should trigger route and container handling warnings.
- hazardous_cargo.json: Hazardous cargo that should trigger special handling and compliance handoff.
- unknown_item_missing_dimensions.json: Shipment with an unknown item to test missing-dimension handling.
- oversized_multi_container.json: Large shipment to test container options and multi-container planning.

## How to Run

Run all scenarios:

python scripts\run_logistics_scenarios.py

Run a single scenario through the full logistics agent report:

python scripts\run_logistics_agent.py data\scenarios\perishable_cargo.json
