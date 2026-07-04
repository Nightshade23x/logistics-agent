# Compliance Agent Contract

## Standard response envelope

`assess_compliance` returns the shared multi-agent contract, same shape as
Risk and Trader's `assess_*` tools (`agent_name`, `status`, `report`,
`handoff_payload`, `handoff_requests`, etc.).

`handoff_payload` includes: `status`, `hazard_class`, `destination_restricted`,
`required_permits`, `required_licenses`, `required_certificates`.

`handoff_requests` declares a dependency on `risk_agent` (destination
sanctions status, to cross-check compliance restrictions).

## Destination-aware checks

`destination_country` is optional on both `check_product_compliance` and
`assess_compliance`. When provided, checks against `country_restrictions.json`
for comprehensive sanctions, hazard-class restrictions, and keyword matches.
Absence of a match does not confirm the destination is unrestricted --
`destination_notes` states this explicitly.

## Granular tools (non-contract, direct use)

`check_product_compliance`, `batch_check_compliance`, `get_hazard_class_info`
remain available for direct queries outside the standard contract.