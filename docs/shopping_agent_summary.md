# Shopping Agent Summary

## Current Version

Shopping Agent V1.3 is complete.

The Shopping Agent helps choose suppliers for requested products. It compares local supplier catalog data and recommends supplier options based on price, quality, rating, lead time, stock, MOQ, user preferences, budget constraints, and supplier risk.

It follows the shared multi-agent contract and prepares handoff data for Finance, Trader, Compliance, and User Agent.

## Main Capabilities

- Reads a shopping request from JSON.
- Reads a shopping request from natural language text.
- Matches requested products to supplier catalog items.
- Handles simple plural matching, such as TV and TVs.
- Compares supplier options by:
  - unit price
  - total estimated cost
  - quality score
  - supplier rating
  - lead time
  - available stock
  - minimum order quantity
- Recommends:
  - cheapest eligible supplier
  - best quality eligible supplier
  - balanced supplier
- Estimates total procurement cost.
- Detects unknown products.
- Detects unavailable options caused by stock or MOQ issues.
- Supports supplier preferences and constraints:
  - preferred supplier countries
  - excluded supplier countries
  - maximum lead time
  - minimum quality score
  - maximum budget
- Filters supplier options that do not meet user preferences.
- Checks whether selected procurement plan is within budget.
- Assesses supplier and procurement risk.
- Adds risk fields to selected suppliers:
  - risk score
  - risk level
  - risk notes
- Adds overall procurement risk summary.

## Natural Language Example

The Shopping Agent can parse text such as:

I need 50 TVs, 5 scooters, and 100 ceramic tiles.
Prefer suppliers from India.
Avoid China.
Maximum lead time 20 days.
Minimum quality score 8.
Budget 13000 USD.

## Main Files

- app/shopping_agent.py: Core supplier matching, filtering, scoring, and procurement planning.
- app/shopping_service.py: Agent contract response, report formatting, handoff payload, and handoff requests.
- app/shopping_text_parser.py: Parses natural language shopping requests.
- app/shopping_risk.py: Supplier and procurement risk scoring.
- scripts/run_shopping_agent.py: Runs the Shopping Agent from JSON or text request files.
- scripts/test_shopping_agent.py: Tests Shopping Agent features.
- data/suppliers/supplier_catalog.json: Local supplier catalog.
- data/suppliers/sample_shopping_request.json: Basic sample JSON request.
- data/suppliers/sample_shopping_request_with_preferences.json: JSON request with supplier preferences and budget constraints.
- data/suppliers/sample_shopping_request_text.txt: Natural language request.

## Agent Output

The Shopping Agent returns:

- agent_name
- status
- summary
- plan
- report
- input_resolution
- missing_information
- handoff_payload
- handoff_requests

## Status Values

ready_for_review:
The agent found eligible suppliers and the plan is usable.

review_required:
The agent found suppliers, but something important needs review, such as the plan exceeding the user budget.

partial_plan_needs_more_information:
Some requested items were planned, but others need clarification.

needs_more_information:
The agent could not create a usable shopping plan.

## Handoff Payload

The handoff payload includes:

- request_id
- customer
- destination_country
- preferred_currency
- preferences
- selected_items
- estimated_total_procurement_cost_usd
- currency
- budget_check
- procurement_risk
- supplier_countries
- product_categories

## Handoff Requests

The Shopping Agent sends information to:

Finance Agent:
For landed cost, ROI, insurance, budget, procurement risk, and financial planning.

Trader Agent:
For HS codes, Incoterms, duties, supplier countries, and trade strategy.

Compliance Agent:
For product restrictions, permits, certificates, supplier country checks, and risk review.

User Agent:
Only when clarification is needed.

## How to Run Tests

Run:

python scripts\test_shopping_agent.py

Expected output:

All shopping agent tests passed.

## How to Run Demo

Run basic JSON request:

python scripts\run_shopping_agent.py

Run JSON request with preferences:

python scripts\run_shopping_agent.py data\suppliers\sample_shopping_request_with_preferences.json

Run natural language request:

python scripts\run_shopping_agent.py data\suppliers\sample_shopping_request_text.txt

## Current Limitations

- Uses a local supplier catalog only.
- Does not search live supplier websites.
- Does not verify real supplier identity.
- Does not calculate landed cost, customs duty, tax, or profit.
- Does not generate purchase orders yet.
- Does not negotiate or contact suppliers.
- Does not calculate shipping requirements. That belongs to the Logistics Agent.

## Future Improvements

Possible next upgrades:

- Purchase order draft generation.
- Supplier shortlist export.
- Integration with Logistics Agent.
- Integration with Finance, Trader, and Compliance agents.
- Better category matching.
- Real supplier API or web search later.
