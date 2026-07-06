# Backend Readiness Checklist

## 1. Purpose

This checklist tracks whether the backend is ready for local demo, partner integration, frontend integration, and live use.

The backend is currently ready for local demo. It is not fully live yet because external partner MCP and REST services have not been connected.

## 2. Local Demo Readiness

Status: READY

Completed:

- User Agent routes requests correctly.
- Shopping Agent handles procurement requests.
- Document AI Agent handles invoice and packing list inputs.
- Logistics Agent creates shipment plans.
- Shopping Agent can hand selected items to Logistics Agent.
- Document AI Agent can hand validated shipment data to Logistics Agent.
- Logistics JSON requests can go directly to Logistics Agent.
- Partner Review Service is included in the flow.
- Final Verdict layer is included in the flow.
- Frontend payload builder produces compact JSON output.
- Health check validates main flows.
- Response contract validator checks agent response structure.
- Full test runner executes all backend tests.

Local demo commands:

    python scripts/run_all_tests.py
    python scripts/show_backend_status.py
    python scripts/demo_user_agent_summary.py

Frontend-style JSON demo:

    python scripts/run_frontend_payload.py json data/suppliers/sample_shopping_request.json

## 3. Core Backend Components

User Agent:

- [x] Intent detection
- [x] Shopping request routing
- [x] Document request routing
- [x] Logistics request routing
- [x] Shopping to Logistics handoff
- [x] Document AI to Logistics handoff
- [x] Partner Review Service call
- [x] Final Verdict attachment
- [x] Frontend payload support

Shopping Agent:

- [x] Supplier matching
- [x] Supplier ranking
- [x] Procurement cost estimate
- [x] Procurement risk estimate
- [x] Draft purchase order support
- [x] Supplier shortlist support
- [x] Handoff payload for Logistics Agent

Document AI Agent:

- [x] Invoice extraction
- [x] Packing list extraction
- [x] Document validation
- [x] Invoice and packing list consistency check
- [x] Handoff payload for Logistics Agent

Logistics Agent:

- [x] Item resolution
- [x] Unit normalization
- [x] CBM calculation
- [x] Shipment weight calculation
- [x] Container recommendation
- [x] Container fit check
- [x] FCL/LCL recommendation
- [x] Packaging and securing plan
- [x] Loading sequence
- [x] Route and handling advice
- [x] Shipment readiness checklist
- [x] Handoff payload for partner and finance checks

Partner Review Service:

- [x] Receives combined shipment and source-agent payload
- [x] Extracts origin, destination, item data, value, CBM, and weight
- [x] Calls Risk adapter placeholder
- [x] Calls Compliance adapter placeholder
- [x] Calls Trader adapter placeholder
- [x] Calls Finance adapter placeholder
- [x] Returns partner_review_not_configured when live services are missing
- [x] Returns needs_more_information when required review inputs are missing

Final Verdict:

- [x] Combines statuses from User Agent and specialist agents
- [x] Detects blocked responses
- [x] Detects review-required responses
- [x] Includes partner review status
- [x] Includes warning messages
- [x] Includes missing information count

## 4. Partner Integration Readiness

Status: PARTIALLY READY

Ready:

- [x] Risk Agent adapter file exists
- [x] Compliance Agent adapter file exists
- [x] Trader Agent adapter file exists
- [x] Finance Agent adapter file exists
- [x] Partner Review Service can call all adapters
- [x] Partner integration config exists
- [x] Environment variable names are documented
- [x] Missing partner connections are reported clearly

Not live yet:

- [ ] Risk MCP server connected
- [ ] Compliance MCP server connected
- [ ] Trader MCP server connected
- [ ] Finance REST API connected
- [ ] Live partner integration tests added
- [ ] Real partner responses included in Final Verdict

Required partner config variables:

    RISK_MCP_SERVER_NAME
    COMPLIANCE_MCP_SERVER_NAME
    TRADER_MCP_SERVER_NAME
    FINANCE_REST_BASE_URL

Example config file:

    config/partner_integrations.example.env

## 5. Frontend Integration Readiness

Status: BACKEND PAYLOAD READY

Ready:

- [x] Compact frontend payload builder exists.
- [x] Frontend payload runner exists.
- [x] Raw backend response is excluded by default.
- [x] Raw backend response can be included with --raw for debugging.
- [x] Logistics metrics are exposed clearly.
- [x] Partner review status is exposed clearly.
- [x] Missing information and assumptions are separated.
- [x] Agent summaries are exposed clearly.

Command:

    python scripts/run_frontend_payload.py json data/suppliers/sample_shopping_request.json

Debug command:

    python scripts/run_frontend_payload.py json data/suppliers/sample_shopping_request.json --raw

Frontend still pending:

- [ ] Build Streamlit or web interface.
- [ ] Add file upload support in frontend.
- [ ] Add text input support in frontend.
- [ ] Add JSON request input support in frontend.
- [ ] Display final verdict clearly.
- [ ] Display agent summaries clearly.
- [ ] Display missing information clearly.
- [ ] Display logistics metrics clearly.

## 6. Testing Readiness

Status: READY FOR LOCAL BACKEND TESTING

Completed tests:

- [x] Partner adapter tests
- [x] Partner config tests
- [x] Backend status tests
- [x] Response contract validator tests
- [x] Partner Review Service tests
- [x] Final Verdict tests
- [x] Frontend payload tests
- [x] User Agent tests
- [x] Shopping Agent tests
- [x] Document AI Agent tests
- [x] Logistics Agent tests
- [x] System health check

Run all tests:

    python scripts/run_all_tests.py

Expected result:

    All tests passed.

## 7. Health Check Readiness

Status: READY

The system health check verifies:

- [x] Shopping JSON flow
- [x] Document to Logistics flow
- [x] Logistics JSON flow
- [x] Partner adapter skeletons
- [x] Final Verdict presence
- [x] User Agent response contract validity
- [x] Partner adapter response contract validity

Command:

    python scripts/system_health_check.py

Expected result:

    System health check passed.

## 8. Current Known Limitations

- Partner checks are not live yet.
- Risk, Compliance, Trader, and Finance adapters return not_configured until external service details are available.
- Final verdict should remain review_required until partner checks are connected.
- Shopping to Logistics flow may use catalog-estimated dimensions when the shopping request does not include exact item dimensions.
- Frontend is not built yet.
- Live API/MCP error handling will need to be tested after partner endpoints are available.

## 9. Before Mentor Demo

Run:

    python scripts/run_all_tests.py
    python scripts/show_backend_status.py
    python scripts/demo_user_agent_summary.py

Check that:

- [ ] All tests pass.
- [ ] Backend status says local_demo_ready_partner_connections_missing.
- [ ] Demo summary shows Shopping, Document AI, Logistics, Partner Review, and Final Verdict flows.
- [ ] Partner Review status is explained as not_configured because live services are not connected yet.
- [ ] Final Verdict is review_required, not clear, because partner checks are not live yet.

## 10. Before Partner Integration

Confirm partner has provided:

- [ ] Risk MCP server name
- [ ] Compliance MCP server name
- [ ] Trader MCP server name
- [ ] Finance REST API base URL
- [ ] Expected request format for each partner service
- [ ] Expected response format for each partner service
- [ ] Example successful responses
- [ ] Example error responses
- [ ] Authentication requirements, if any
- [ ] Rate limits or timeout requirements, if any

After receiving partner details:

- [ ] Add environment variables locally.
- [ ] Replace placeholder adapter behavior with live calls.
- [ ] Add integration tests for configured endpoints.
- [ ] Update Final Verdict logic if live partner statuses introduce new status values.
- [ ] Update backend architecture documentation.
- [ ] Update demo guide.

## 11. Before Live Use

Required before live use:

- [ ] Live partner services connected.
- [ ] Live partner tests passing.
- [ ] API/MCP timeout handling tested.
- [ ] API/MCP error handling tested.
- [ ] Sensitive config kept out of Git.
- [ ] Frontend tested with text, JSON, and file inputs.
- [ ] Final verdict reviewed with realistic shipment examples.
- [ ] User-facing wording reviewed.
- [ ] Edge cases tested.

## 12. Current Readiness Summary

Local backend demo:

    READY

Frontend payload:

    READY

Partner integration structure:

    READY

Live partner integration:

    WAITING FOR PARTNER MCP AND REST DETAILS

Production/live use:

    NOT READY YET

## 13. New Backend Service Layer Readiness

Status: READY

Completed:

- [x] Backend service facade exists.
- [x] Frontend-style requests go through backend_service.
- [x] Text requests supported through backend_service.
- [x] JSON file requests supported through backend_service.
- [x] Document file requests supported through backend_service.
- [x] Backend validation is attached to service responses.
- [x] Request metadata is attached to service responses.
- [x] Safe error payloads are returned for backend service failures.
- [x] Raw response is excluded by default.
- [x] Raw response can still be included for debugging.

Main backend service file:

    app/backend_service.py

Frontend-facing command:

    python scripts/run_frontend_payload.py json data/suppliers/sample_shopping_request.json

## 14. Partner Request Builder Readiness

Status: READY

Completed:

- [x] Combined partner review payload validator exists.
- [x] Partner request builder exists.
- [x] Risk Agent request object is generated.
- [x] Compliance Agent request objects are generated.
- [x] Trader Agent request objects are generated.
- [x] Finance Agent request object is generated.
- [x] Partner Review Service uses the request builder.
- [x] Partner request builder tests are included in the full test runner.
- [x] Partner request export script exists.

Main files:

    app/partner_review_payload_validator.py
    app/partner_request_builder.py
    app/partner_review_service.py

Export command:

    python scripts/export_partner_agent_requests.py

## 15. Demo Bundle Export Readiness

Status: READY

Completed:

- [x] Backend status export included.
- [x] Frontend payload export included.
- [x] Partner review payload export included.
- [x] Individual partner agent request export included.
- [x] Generated outputs are written to demo_outputs.
- [x] demo_outputs is ignored by Git.

Command:

    python scripts/export_backend_demo_bundle.py

Expected generated files:

    demo_outputs/backend_status.json
    demo_outputs/frontend_payload_shopping.json
    demo_outputs/partner_review_payload.json
    demo_outputs/partner_agent_requests.json

## 16. Updated Standard Backend Check

Before showing the backend, run:

    python scripts/run_all_tests.py
    python scripts/show_backend_status.py
    python scripts/demo_user_agent_summary.py
    python scripts/export_backend_demo_bundle.py

Expected result:

- all tests pass
- backend status says local_demo_ready_partner_connections_missing
- demo summary runs successfully
- demo bundle exports successfully
