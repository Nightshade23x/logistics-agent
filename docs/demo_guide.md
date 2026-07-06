# Demo Guide

## 1. Current Progress

This project currently has an integrated multi-agent workflow for trade, shopping, document validation, logistics planning, partner review preparation, and final verdict generation.

Completed agents on our side:

- User Agent: routes user requests and coordinates specialist agents.
- Shopping Agent: selects suppliers, estimates procurement cost and procurement risk, and creates draft purchase orders.
- Document AI Agent: extracts and validates trade documents such as invoices and packing lists.
- Logistics Agent: calculates CBM, weight, container recommendation, packaging plan, loading sequence, route handling, and readiness status.

Partner integration skeletons are also included:

- Risk Agent adapter
- Compliance Agent adapter
- Trader Agent adapter
- Finance Agent adapter
- Partner Review Service

These partner adapters currently return not_configured until the live MCP and REST connection details are available.

## 2. Main Demo Commands

Run these from the project root:

    python scripts\system_health_check.py
    python scripts\demo_user_agent_summary.py

The first command checks that the system is healthy.
The second command shows a concise mentor-friendly demo.

## 3. Full Test Command

Run this before showing the project:

    python scripts\test_partner_adapters.py
    python scripts\test_partner_review_service.py
    python scripts\test_final_verdict.py
    python scripts\test_user_agent.py
    python scripts\test_shopping_agent.py
    python scripts\test_document_agent.py
    python scripts\test_logistics_agent.py
    python scripts\system_health_check.py

## 4. Demo 1: Shopping JSON Flow

Command:

    python scripts\run_user_agent.py json data\suppliers\sample_shopping_request.json

Expected flow:

    Shopping JSON request
    -> User Agent
    -> Shopping Agent
    -> Logistics Agent
    -> Partner Review Service
    -> Final Verdict

Important output to point out:

- Detected intent: shopping
- Agents called: shopping_agent, logistics_agent, partner_review_service
- Shopping Agent selects suppliers and estimates procurement cost.
- Logistics Agent calculates CBM, total weight, container recommendation, packaging, loading, and readiness.
- Partner Review returns partner_review_not_configured until live partner services are connected.
- Final verdict is review_required because partner checks are not live yet.

## 5. Demo 2: Document AI to Logistics Flow

Command:

    python scripts\run_user_agent.py files data\documents\sample_invoice.txt data\documents\sample_packing_list.txt

Expected flow:

    Invoice and packing list
    -> User Agent
    -> Document AI Agent
    -> Logistics Agent
    -> Partner Review Service
    -> Final Verdict

Important output to point out:

- Detected intent: document
- Agents called: document_ai_agent, logistics_agent, partner_review_service
- Document AI validates invoice and packing list consistency.
- Logistics Agent uses validated document item data for shipment planning.
- Final verdict is review_required because logistics risk and partner checks still require review.

## 6. Demo 3: Plain English Shopping Request

Command:

    python scripts\run_user_agent.py text "I need 50 TVs, 5 scooters, and 100 ceramic tiles. Prefer suppliers from India. Avoid China. Budget 13000 USD."

Expected flow:

    Plain-English request
    -> User Agent
    -> Shopping Agent
    -> Logistics Agent
    -> Partner Review Service
    -> Final Verdict

Important note:

This demo does not include a destination country, so the partner review layer correctly asks for more information instead of guessing.

## 7. Clean Summary Demo

For mentor demos, use this command because it prints a shorter summary:

    python scripts\demo_user_agent_summary.py

This shows:

- Shopping JSON flow
- Document AI to Logistics flow
- Plain-English shopping flow
- Agents called
- Key logistics metrics
- Partner review status
- Final verdict

## 8. Health Check

Use this command to quickly prove the system is working:

    python scripts\system_health_check.py

The health check verifies:

- Shopping JSON flow
- Document to Logistics flow
- Logistics JSON flow
- Partner adapter skeletons
- Final verdict presence

## 9. Remaining Work

Next steps:

1. Connect partner MCP servers for Risk, Compliance, and Trader.
2. Connect partner Finance REST API.
3. Replace placeholder partner review responses with live results.
4. Add final combined logistics-manager summary once live partner responses are available.
5. Build or connect the frontend or AI interface after backend orchestration is stable.

## 10. One-Command Full Test Runner

Instead of running every test manually, use:

    python scripts\run_all_tests.py

This runs:

- partner adapter tests
- partner review service tests
- final verdict tests
- frontend payload tests
- user agent tests
- shopping agent tests
- document agent tests
- logistics agent tests
- system health check

## 11. Frontend Payload Runner

Use this command to see the clean JSON payload that a frontend or AI interface can consume:

    python scripts\run_frontend_payload.py json data\suppliers\sample_shopping_request.json

This returns a compact payload with:

- decision
- agents_called
- logistics_metrics
- partner_review_status
- missing_information
- assumptions
- agent_summaries

By default, raw full reports are excluded so the frontend payload stays readable.

For debugging, include the full raw response:

    python scripts\run_frontend_payload.py json data\suppliers\sample_shopping_request.json --raw

## 12. Backend Service Facade

The frontend-style runner now goes through the backend service facade.

Command:

    python scripts/run_frontend_payload.py json data\suppliers\sample_shopping_request.json

This internally uses:

    app/backend_service.py

The backend service adds:

- compact frontend payload
- backend validation
- request metadata
- safe error handling
- optional raw response support

Normal frontend output excludes raw_response.

Debug mode:

    python scripts/run_frontend_payload.py json data\suppliers\sample_shopping_request.json --raw

## 13. Backend Demo Bundle

Use this command to export a complete backend demo bundle:

    python scripts/export_backend_demo_bundle.py

It generates:

- backend_status.json
- frontend_payload_shopping.json
- partner_review_payload.json
- partner_agent_requests.json

Output folder:

    demo_outputs/

This folder is ignored by Git because the files are generated.

## 14. Partner Handoff Export Commands

Combined partner review payload:

    python scripts/export_partner_review_payload.py

Individual partner-agent request objects:

    python scripts/export_partner_agent_requests.py

These are useful for showing the partner exactly what data will be sent to Risk, Compliance, Trader, and Finance agents.

## 15. Updated Recommended Demo Sequence

Run this sequence before a mentor or partner demo:

    python scripts/run_all_tests.py
    python scripts/show_backend_status.py
    python scripts/demo_user_agent_summary.py
    python scripts/run_frontend_payload.py json data\suppliers\sample_shopping_request.json
    python scripts/export_backend_demo_bundle.py

Main points to explain:

- backend is ready for local demo
- partner adapters are ready but not connected to live services yet
- final verdict stays review_required until partner services are live
- frontend-style payload is available through backend_service
- partner handoff payloads can be exported clearly
