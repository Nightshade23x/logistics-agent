# Backend Architecture

## 1. Purpose

This backend is a multi-agent trade, procurement, document validation, and logistics planning system.

The goal is to take a user request, route it to the correct specialist agents, combine the results, prepare partner-agent checks, and return a final review verdict.

## 2. Main Backend Components

### User Agent

The User Agent is the main orchestrator.

It is responsible for:

- detecting request intent
- routing the request to the correct specialist agent
- managing handoffs between agents
- calling partner review preparation
- attaching the final verdict
- preparing a response that the frontend can consume

The User Agent should remain the central controller. The frontend should only act as the user interface.

### Shopping Agent

The Shopping Agent handles procurement-related requests.

It is responsible for:

- parsing shopping requests
- matching requested products to suppliers
- ranking supplier options
- estimating procurement cost
- assessing procurement risk
- creating draft purchase orders
- preparing selected items for Logistics Agent handoff

### Document AI Agent

The Document AI Agent handles uploaded trade documents.

It is responsible for:

- reading invoice and packing list data
- extracting shipment fields
- validating document completeness
- checking invoice and packing list consistency
- preparing verified item data for Logistics Agent handoff

### Logistics Agent

The Logistics Agent handles shipment planning.

It is responsible for:

- resolving item dimensions and weights
- calculating total CBM
- calculating total shipment weight
- recommending container type
- checking container fit
- recommending FCL or LCL
- creating packaging and securing plans
- creating loading sequence and layout guidance
- identifying operational logistics risk
- preparing handoff data for partner and finance checks

### Partner Review Service

The Partner Review Service prepares calls to external partner agents.

It currently coordinates:

- Risk Agent
- Compliance Agent
- Trader Agent
- Finance Agent

At the moment, these adapters are backend-ready but return not_configured until live MCP server names and Finance REST API details are provided.

### Final Verdict Layer

The Final Verdict layer combines agent statuses into one decision.

Possible high-level outcomes include:

- clear
- review_required
- blocked

The verdict helps the frontend and user understand whether the shipment is ready, needs review, or cannot continue.

### Frontend Payload Builder

The frontend payload builder converts the full backend response into a compact JSON structure.

It includes:

- decision
- agents_called
- short_answer
- logistics_metrics
- partner_review_status
- missing_information
- assumptions
- agent_summaries

By default, it excludes raw full reports so the frontend output stays readable.

## 3. Main Request Flows

### Flow 1: Shopping JSON Request

    Shopping JSON request
    -> User Agent
    -> Shopping Agent
    -> Logistics Agent
    -> Partner Review Service
    -> Final Verdict
    -> Frontend Payload

This flow is used when the user provides structured shopping/procurement data.

### Flow 2: Plain-English Shopping Request

    Plain-English request
    -> User Agent
    -> Shopping Agent
    -> Logistics Agent
    -> Partner Review Service
    -> Final Verdict
    -> Frontend Payload

This flow is used when the user asks for products in natural language.

If important details such as destination country are missing, the backend should ask for more information instead of guessing.

### Flow 3: Document Upload Request

    Invoice and packing list
    -> User Agent
    -> Document AI Agent
    -> Logistics Agent
    -> Partner Review Service
    -> Final Verdict
    -> Frontend Payload

This flow is used when the user uploads shipment documents.

The Document AI Agent validates the documents first. If the item data is usable, it is handed to the Logistics Agent.

### Flow 4: Logistics JSON Request

    Logistics JSON request
    -> User Agent
    -> Logistics Agent
    -> Partner Review Service
    -> Final Verdict
    -> Frontend Payload

This flow is used when shipment item data is already available.

## 4. Partner Integration Design

The backend has adapter skeletons for partner services.

Partner integrations are configured through environment variables:

- RISK_MCP_SERVER_NAME
- COMPLIANCE_MCP_SERVER_NAME
- TRADER_MCP_SERVER_NAME
- FINANCE_REST_BASE_URL

Example config file:

    config/partner_integrations.example.env

Current behavior:

- If partner connections are missing, adapters return not_configured.
- The system still works for local demo mode.
- Final verdict becomes review_required because live partner checks are not complete.

Future behavior:

- Risk Agent will check country-level risk and sanctions.
- Compliance Agent will check product restrictions, permits, and documents.
- Trader Agent will classify products, HS codes, duties, and trade strategy.
- Finance Agent will calculate landed cost, freight, insurance, tax, and ROI.

## 5. Response Contract

Every specialist agent response should include:

- agent_name
- status
- summary

The User Agent response should include:

- agent_name
- status
- summary
- detected_intent
- agents_called
- specialist_responses
- final_verdict

The response contract validator checks these fields during testing and health checks.

## 6. Backend Validation Tools

### Full test runner

    python scripts/run_all_tests.py

This runs all local backend tests.

### System health check

    python scripts/system_health_check.py

This checks that the main flows work and that response contracts are valid.

### Backend status report

    python scripts/show_backend_status.py

This shows whether the backend is ready for local demo and whether live partner integrations are configured.

### Frontend payload runner

    python scripts/run_frontend_payload.py json data/suppliers/sample_shopping_request.json

This shows the compact JSON payload that a frontend or AI interface can consume.

## 7. Current Backend Status

The backend is currently ready for local demo.

Ready components:

- User Agent
- Shopping Agent
- Document AI Agent
- Logistics Agent
- Partner Review Service
- Final Verdict
- Frontend Payload Builder
- Partner adapter skeletons
- Response contract validation
- Health checks
- Full test runner

Not live yet:

- Risk MCP server
- Compliance MCP server
- Trader MCP server
- Finance REST API

Because partner services are not live yet, final shipment decisions should remain review_required instead of clear.

## 8. Recommended Demo Commands

Run these before showing the project:

    python scripts/run_all_tests.py
    python scripts/show_backend_status.py
    python scripts/demo_user_agent_summary.py

For frontend-style JSON output:

    python scripts/run_frontend_payload.py json data/suppliers/sample_shopping_request.json

## 9. Next Backend Steps

1. Connect live Risk MCP server.
2. Connect live Compliance MCP server.
3. Connect live Trader MCP server.
4. Connect live Finance REST API.
5. Replace placeholder adapter responses with real partner service calls.
6. Add integration tests using configured partner test endpoints when available.
7. Add final combined logistics-manager answer after live partner responses are available.
