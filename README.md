@'
# Logistics Agent

This project is an AI-based logistics and shipping agent. The goal is to help users plan shipments by calculating cargo volume, recommending containers, suggesting loading strategies, checking shipment risks, and later handling regulations, routing, insurance, and visual container layouts.

## Initial Goal

Version 1 will focus on a simple working prototype:

1. Accept a list of shipment items.
2. Calculate CBM/cubic meters.
3. Classify cargo types such as fragile, heavy, perishable, hazardous, or high value.
4. Recommend a suitable container.
5. Provide basic loading advice.

## Planned Modules

- Cargo input parser
- CBM calculator
- Cargo classifier
- Container recommender
- Loading advice module
- Regulations checker
- Route and handling advisor
- Insurance/risk advisor
- Visual container loading module

## Collaboration Workflow

The `main` branch should stay stable. New work should be done on feature branches, for example:

- feature/cbm-calculator
- feature/cargo-classifier
- feature/loading-rules
- feature/regulations-checker

Each feature should be committed and pushed separately, then merged after review.
