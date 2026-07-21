# Logistics Agent — System Architecture

> Audience: this document is written so that another LLM (or engineer) with **zero prior context** on this repo can understand what the system is, how data flows through it, and exactly what a caller sends in / gets back on each call. It is derived directly from the source in
> `logistics-agent-avishi-frontend-on-partner-integration/` (README.md, docs/backend_architecture.md, docs/frontend_payload_contract.md, and the `app/` source files).

---

## 1. What this system is

A modular, Python, multi-agent **trade / procurement / logistics planning backend**. It is not a single model call — it is a deterministic pipeline of Python "agent" modules that:

1. Accepts a request in one of three shapes: free-text, a structured shopping JSON file, or uploaded trade documents (invoice / packing list / bill of lading / certificate of origin).
2. Routes the request to the right specialist agent(s) based on detected intent.
3. Runs procurement, logistics, and document-validation logic (pure Python — no LLM required for the core math/rules).
4. Optionally calls **external partner agents** (Risk, Compliance, Trader, Finance) through a Trade Orchestrator adapter, degrading gracefully if they are offline.
5. Combines everything into a single **final verdict**.
6. Flattens the whole thing into a **frontend-ready JSON payload** so a UI (web, Streamlit, Gemini chat surface, etc.) never has to parse raw agent text.

There is an optional Gemini-based "smart answer" layer (`app/smart_answer.py`) that can turn the structured payload into a natural-language explanation, but the core backend does not require an LLM to produce a correct, structured result — the LLM is a presentation layer on top, not the source of truth.

---

## 2. High-level component map

```
User / Frontend / Gemini
        |
        v
  app/backend_service.py        <-- SINGLE recommended entry point for callers
        |
        v
  app/user_agent.py             (the orchestrator / "User Agent")
        |
        |-- detects intent (app/agent_router.py, app/text_request_intent.py)
        |
        |-- Flow: shopping     -> app/shopping_agent.py
        |-- Flow: logistics    -> app/logistics_agent.py
        |-- Flow: documents    -> app/document_service.py, app/document_parser.py, app/document_validator.py
        |
        |-- handoff -> app/logistics_agent.py (always runs after shopping/documents to plan the physical shipment)
        |
        |-- app/partner_review_service.py
        |        -> app/partner_request_builder.py (splits payload per partner)
        |        -> app/partner_adapters/trade_orchestrator_client.py
        |               -> external Risk Agent (MCP)
        |               -> external Compliance Agent (MCP)
        |               -> external Trader Agent (MCP)
        |               -> external Finance Agent (REST, FastAPI service in finance_agent/)
        |
        |-- app/final_verdict.py  (combines all agent statuses into one decision)
        v
  raw_response (dict) — the User Agent's full internal response
        |
        v
  app/frontend_payload.py / app/compact_frontend_payload.py
        |
        v
  app/backend_service.py enriches with:
     shopping_quality_review, procurement_advice, logistics_quality_review,
     document_quality_review, trade_terms_advice, insurance_advice,
     document_requirements_advice, landed_cost_advice,
     trade_compliance_readiness, clarification_questions,
     booking_readiness, final_answer, action_plan,
     executive_summary, ui_sections, backend_validation, request_metadata
        |
        v
  Final JSON payload returned to caller (see §5)
```

### Key module responsibilities

| Module | Role |
|---|---|
| `app/backend_service.py` | **Public facade.** Exposes `process_text_request`, `process_json_file_request`, `process_document_files_request`. Callers (frontend, API layer, Gemini tool-call) should only ever call these three functions — never import internal agent modules directly. Wraps everything in try/except and always returns a well-formed payload (even on error, see §5.9). |
| `app/user_agent.py` (~1284 lines) | The orchestrator. Detects intent, calls the correct specialist agent(s), manages handoffs (shopping → logistics, documents → logistics), calls the partner review service, attaches the final verdict, and returns the "raw_response" contract described in §4. |
| `app/agent_router.py` / `app/text_request_intent.py` | Classifies free-text or file input into one of: `shopping`, `logistics`, `document`, `unknown`, using keyword scoring (e.g. "supplier", "budget" → shopping; "container", "cbm", "fcl" → logistics; "invoice", "packing list" → document). |
| `app/shopping_agent.py` + `app/procurement_advisor.py` + `app/shopping_quality_review.py` | Procurement: selects suppliers from a catalog, ranks options, estimates cost, assesses risk, builds a draft purchase order, and prepares selected items for the Logistics Agent handoff. |
| `app/logistics_agent.py` (~342 lines, entry point `build_logistics_plan(items)`) | Physical shipment planning: resolves item dimensions/weight (via `item_resolver.py` if not supplied), computes total CBM and weight (`container_fit.py`, `container_options.py`), recommends a container + FCL/LCL (`container_strategy.py`), builds a packaging/loading/route plan (`packaging_advisor.py`, `loading_planner.py`, `route_advisor.py`), flags operational risk (`logistics_risk.py`), and produces the `logistics_visualizer` payload (`container_layout.py`, `ui_sections_builder.py` helpers). |
| `app/document_service.py`, `document_parser.py`, `document_validator.py`, `document_pair_service.py`, `document_set_service.py`, `document_quality_review.py`, `document_requirements_advisor.py` | Document AI: extracts fields/items from invoice, packing list, bill of lading, certificate of origin; validates document quality; cross-checks invoice vs packing list; checks completeness of the document set; prepares verified item data to hand off to the Logistics Agent. |
| `app/partner_review_service.py`, `app/partner_request_builder.py`, `app/partner_adapters/*` | Prepares and (if configured) sends requests to 4 external partner services: Risk, Compliance, Trader (all via an MCP-style Trade Orchestrator), and Finance (a separate FastAPI REST service, see §3). Returns `not_configured` status per-partner when env vars are missing, rather than failing the whole request. |
| `app/final_verdict.py` | Merges every specialist agent's status (`ok` / `needs_review` / `blocked` / `not_configured`, etc.) into one of: `clear`, `review_required`, `blocked`. |
| `app/response_contract_validator.py` | Validates that the User Agent's raw response has the required shape (`agent_name`, `status`, `summary`, `detected_intent`, `agents_called`, `specialist_responses`, `final_verdict`). Result is surfaced to the caller as `backend_validation`. |
| `app/frontend_payload.py` / `app/compact_frontend_payload.py` | Convert the verbose raw_response into a UI-friendly structure (decision, agents_called, short_answer, logistics_metrics, partner_review_status, missing_information, assumptions, agent_summaries, logistics_visualizer). By default raw text reports are excluded to keep the payload small. |
| `app/executive_summary_builder.py`, `ui_sections_builder.py`, `action_plan_builder.py`, `final_answer_builder.py`, `booking_readiness_advisor.py`, `clarification_questions.py` | Presentation-layer builders that turn the enriched payload into ready-to-render UI blocks: a top summary card, section cards (Executive Decision / Shipment Snapshot / Procurement / Logistics / Compliance & Documents / Costs & Insurance / Partner Checks / Next Actions), an action checklist, and a booking-readiness score/gate. |
| `app/trade_terms_advisor.py`, `insurance_advisor.py`, `landed_cost_advisor.py`, `document_requirements_advisor.py`, `trade_compliance_readiness_advisor.py` | Trade-domain advisors that reason over Incoterms, insurance needs, landed cost inputs, required documents, and overall compliance readiness — each returns `applicable`, `status`, `summary`, `warnings`, `blockers`, `recommendations`. |
| `app/smart_answer.py` | Optional: calls Google Gemini (`get_gemini_api_key`, `get_gemini_model`) to turn the structured payload into a natural-language answer. Not required for the core pipeline to function. |
| `app/streamlit_frontend.py` (~2669 lines) | The existing reference frontend implementation (Streamlit + injected CSS). This is what the improved `demo.html` in this deliverable is modeled on / improves upon. |
| `finance_agent/` (separate FastAPI/REST service) | External partner: computes freight cost, insurance cost, import duty, tax, ROI, landed cost. Called via HTTP (`/finance/*` routes). |
| `compliance_agent/` (separate MCP server, `FastMCP`) | External partner: hazard classification, restricted-product and country-restriction checks. Exposes MCP tools (`check_product_compliance`, `batch_check_compliance`, `assess_compliance`), not a REST API. |
| `risk_agent/` (separate MCP server, `FastMCP`) | External partner: country corruption-risk score (CPI) and sanctions status. Exposes MCP tools (`get_country_risk_score`, `get_country_sanctions`, `assess_trade_risk`). |
| `trader_agent/` (separate MCP server, `FastMCP`) | External partner: Incoterm lookup, HS code classification, duty calculation, FTA check, export strategy. Exposes MCP tools (`explain_incoterm`, `classify_hs_code`, `calculate_duty`, `check_fta`, `suggest_export_strategy`, `plan_export`, `assess_trade_plan`, `assess_trade_plan_with_reasoning`). Uses Gemini (`gemini-2.5-flash`) for the reasoning variant, not OpenAI. |
| `orchestrator_agent/` (separate FastAPI service, `POST /orchestrate`) | The Trade Orchestrator itself. Fans out to `risk_agent`, `compliance_agent`, `trader_agent` (via MCP client) and `finance_agent` (via REST), reconciles Trader's duty rate into Finance's cost figures, derives a rule-based verdict, and synthesizes one human-readable answer. Full contract in §3a below. |

---

## 3. Request flows (exact routing)

There are 4 canonical flows, all converging on the same output contract:

```
Flow 1 — Structured shopping JSON
  shopping JSON --> User Agent --> Shopping Agent --> Logistics Agent --> Partner Review Service --> Final Verdict --> Frontend Payload

Flow 2 — Plain-English shopping request
  free text --> User Agent (intent = shopping) --> Shopping Agent --> Logistics Agent --> Partner Review Service --> Final Verdict --> Frontend Payload
  (if required fields such as destination_country are missing, the backend asks clarifying questions instead of guessing)

Flow 3 — Document upload
  invoice + packing list (+ BOL / certificate of origin) --> User Agent (intent = document) --> Document AI Agent --> Logistics Agent --> Partner Review Service --> Final Verdict --> Frontend Payload

Flow 4 — Logistics-only JSON (item data already known)
  shipment items JSON --> User Agent (intent = logistics) --> Logistics Agent --> Partner Review Service --> Final Verdict --> Frontend Payload
```

Intent detection for free text/files is keyword-based (see `agent_router.py`):
- shopping keywords: buy, source, supplier(s), shopping, purchase, order, budget, "prefer suppliers", avoid
- document keywords: invoice, packing list, bill of lading, certificate of origin, document(s)
- logistics keywords: shipment, shipping, container, cbm, cargo, freight, lcl, fcl, fit, loading, packaging
- file extension `.txt/.pdf/.docx` → forced to `document` intent
- highest keyword-count wins; all-zero → `unknown`

### Partner integration (external, optional)

Configured via environment variables (`config/partner_integrations.example.env`):
- `RISK_MCP_SERVER_NAME`
- `COMPLIANCE_MCP_SERVER_NAME`
- `TRADER_MCP_SERVER_NAME`
- `FINANCE_REST_BASE_URL` (defaults to a locally-run `finance_agent` FastAPI service, e.g. `http://127.0.0.1:8003`)
- `TRADE_ORCHESTRATOR_BASE_URL` (a separate orchestrator service that fans out to Risk/Compliance/Trader)

Behavior:
- If any partner integration is not configured, its adapter returns `not_configured` — the pipeline still completes and returns a valid payload (`partner_review_status: "partner_review_not_configured"`).
- Because live partner checks are incomplete in that case, `final_verdict.verdict` is forced to at best `review_required`, never `clear`.
- When the orchestrator **is** connected, `partner_review_status` reflects the live result (e.g. `review_required`, `clear`, `blocked`), aggregating Risk/Compliance/Trader/Finance responses.

---

## 3a. Inside the Trade Orchestrator (`orchestrator_agent/`)

From the User Agent's point of view, the Trade Orchestrator is one black-box partner service reached over HTTP. From the inside, it is its own small multi-agent system with its own contract, documented here so a caller (or another LLM) doesn't have to guess what's behind `TRADE_ORCHESTRATOR_BASE_URL`.

**Endpoint:** `POST /orchestrate`

**Request**
```json
{ "query": "ship 200 e-bike batteries from China to Brazil" }
```
A single free-text field. There is no structured request shape — the orchestrator parses free text itself.

**Internal pipeline (`orchestrator_service.py`):**
1. `ShipmentParserService.parse(query)` — uses Gemini (`shared_llm_client.py`, model `gemini-2.5-flash`) to extract a structured `ParsedShipment`: `product_description, country_from, country_to, target_market, quantity, cargo_value, weight_kg, volume_m3, currency`. If Gemini is unavailable, rate-limited, or returns invalid JSON, falls back to deterministic regex extraction — the endpoint never 500s because of the LLM.
2. Calls `risk_agent.assess_trade_risk(country=country_to)` (MCP tool call).
3. Calls `compliance_agent.assess_compliance(product_description, destination_country=country_to)` (MCP tool call).
4. Calls `trader_agent.assess_trade_plan(product_description, country_from, country_to, target_market)` (MCP tool call).
5. Calls `finance_agent` over REST with a `Shipment` built from the parsed fields (`transport_mode` hardcoded to `"sea"`, `insurance_required=True`). If Trader returned a `duty_rate_percent`, the orchestrator recalculates `import_duty`/`landed_cost`/`total_cost` using that rate instead of Finance's default.
6. Each of the four calls is wrapped in its own try/except — a failure populates `agent_errors[agent_name]` but does not stop the other three calls or fail the request.
7. `VerdictService` derives `clear` / `review_required` / `blocked` from the four reports.
8. `SynthesisService` writes one human-readable `synthesis` string.

**Response (`OrchestratedResponse`)**
```json
{
  "request_id": "uuid",
  "parsed_shipment": { "product_description": "...", "country_from": "...", "country_to": "...", "target_market": "...", "quantity": 200, "cargo_value": 50000.0, "weight_kg": 800.0, "volume_m3": 2.5, "currency": "USD" },
  "risk_report": { "...AgentResponse from risk_agent..." },
  "compliance_report": { "...AgentResponse from compliance_agent..." },
  "trader_report": { "...AgentResponse from trader_agent..." },
  "finance_report": { "freight_cost": 0, "insurance_cost": 0, "import_duty": 0, "taxes": 0, "landed_cost": 0, "currency": "USD", "total_cost": 0, "estimated_profit": 0 },
  "agent_errors": { },
  "verdict": {
    "status": "clear | review_required | blocked",
    "headline": "one-sentence summary",
    "blockers": [], "warnings": [], "next_steps": []
  },
  "synthesis": "final human-readable answer"
}
```
`agent_errors` maps agent name → error string only for agents that failed; it's empty when all four succeed.

**How Samar's backend consumes this:** `app/partner_adapters/trade_orchestrator_client.py` converts its own structured payload into one free-text `query` (via `build_trade_orchestrator_query`), POSTs it here, then `normalize_trade_orchestrator_response()` maps `verdict.status` (`clear/review_required/blocked`) onto Samar's own vocabulary (`ready_for_review/review_required/blocked`) and flattens `risk_report`/`compliance_report`/`trader_report`/`finance_report` into its `handoff_payload`.

**Also exposed:** `GET /health` → `{"status": "ok", "agent": "orchestrator_agent"}` — a plain liveness check, no auth, no body.

---

## 4. The internal contract: `raw_response` (User Agent output, pre-frontend-shaping)

Every specialist agent response must include: `agent_name`, `status`, `summary`.

The **User Agent's** top-level `raw_response` must include:

```text
agent_name           str   e.g. "user_agent"
status               str   e.g. "review_required"
summary              str   human-readable summary
detected_intent       str   "shopping" | "logistics" | "document" | "unknown"
agents_called         list  which specialist agents ran, e.g. ["shopping_agent", "logistics_agent", "partner_review_service"]
specialist_responses  dict  each specialist agent's own {agent_name, status, summary, ...} block
final_verdict         dict  {verdict, agent_statuses, blockers, warnings, missing_information_count, partner_review_status}
```

`app/response_contract_validator.py` checks this shape; the result becomes the caller-visible `backend_validation` field. This is the internal contract — most external callers should not consume `raw_response` directly, they should consume the enriched payload in §5 (unless `include_raw_response=True` is explicitly passed for debugging).

---

## 5. THE CALL CONTRACT — per-call input / output

This is the part most relevant to any caller (frontend, API gateway, or another LLM/agent) integrating with this backend. There are exactly **three entry-point functions**, all in `app/backend_service.py`. Import and call these directly; do not import the internal agent modules.

### 5.1 `process_text_request(user_text: str, include_raw_response: bool = False) -> dict`

**Input**
```text
user_text: str                 — free-form natural-language request
include_raw_response: bool     — if True, adds the internal raw_response dict to the output for debugging
```
Example input:
```text
"I need 50 TVs, 5 scooters, and 100 ceramic tiles. Prefer suppliers from India. Avoid China. Budget 13000 USD."
```

**Internally**: calls `run_user_agent_from_text(user_text)` → intent classified as `shopping` (keyword hits: "prefer suppliers", "avoid", "budget") → Shopping Agent → Logistics Agent handoff → Partner Review Service → Final Verdict → same enrichment pipeline as all other flows (§5.4).

**Output**: the full enriched JSON payload described in §5.4. `request_metadata.request_type == "text"`, `request_metadata.input_source == user_text`.

---

### 5.2 `process_json_file_request(json_path: str | Path, include_raw_response: bool = False) -> dict`

**Input**
```text
json_path: str | Path   — path to a structured request JSON file (shopping-style or logistics-style)
```
Example input file (`data/suppliers/sample_shopping_request.json`):
```json
{
  "request_id": "SHOP-REQ-001",
  "customer": "Demo Customer",
  "destination_country": "USA",
  "preferred_currency": "USD",
  "items": [
    { "name": "TVs", "quantity": 50 },
    { "name": "Scooters", "quantity": 5 },
    { "name": "Ceramic tiles", "quantity": 100 }
  ]
}
```
Item objects may also carry physical attributes directly (used by the Logistics Agent if present, otherwise resolved via `app/item_resolver.py` from a lookup table):
```json
{
  "name": "TV", "quantity": 50,
  "length_m": 1.2, "width_m": 0.2, "height_m": 0.8, "weight_kg": 12,
  "fragile": true, "stackable": false
}
```

**Internally**: `run_user_agent_from_json_file(path)` → intent inferred from JSON shape (has `items` + shopping fields → shopping flow; pure shipment items → logistics flow) → same downstream pipeline as §5.1.

**Output**: the full enriched JSON payload (§5.4). `request_metadata.request_type == "json_file"`, `request_metadata.input_source == str(path)`.

---

### 5.3 `process_document_files_request(file_paths: list[str | Path], include_raw_response: bool = False) -> dict`

**Input**
```text
file_paths: list[str | Path]   — one or more uploaded document files, e.g. [invoice.txt, packing_list.txt]
```
Supported document types: invoice, packing list, bill of lading, certificate of origin (parsed as text/PDF/docx via `app/document_parser.py`).

**Internally**: `run_user_agent_from_files(paths)` → forced intent `document` (based on file extensions) → Document AI Agent extracts fields + items, validates document quality, cross-checks invoice vs packing list (`document_pair_service.py`), checks set completeness (`document_set_service.py`) → hands verified items to Logistics Agent → Partner Review Service → Final Verdict → same enrichment pipeline.

**Output**: the full enriched JSON payload (§5.4). `request_metadata.request_type == "document_files"`, `request_metadata.input_source == [str(p) for p in paths]`.

---

### 5.4 Common output shape (all three functions return this same structure)

This is the **compact/enriched frontend payload** — the thing a UI or another agent should actually consume. Fields, in the backend's recommended render order:

```jsonc
{
  "payload_type": "compact_frontend_payload",   // (present when using compact builder; backend_service enriches the full frontend_payload with the same conceptual fields)
  "agent_name": "user_agent",
  "status": "review_required",
  "decision": "review_required",                 // "clear" | "review_required" | "blocked"
  "detected_intent": "shopping",                 // "shopping" | "logistics" | "document" | "unknown"
  "agents_called": ["shopping_agent", "logistics_agent", "partner_review_service"],
  "short_answer": "...",

  "logistics_metrics": {
    "total_cbm": 19.41,
    "total_weight_kg": 2250.0,
    "recommended_container": "20ft Standard Container",
    "recommended_load_type": "fcl_preferred",
    "risk_level": "high",
    "risk_score": 6,
    "readiness_status": "ready_for_review_with_high_risk"
  },

  "logistics_visualizer": {
    "visualizer_type": "container_load_visualizer",
    "status": "available",
    "container": {                    // selected container + utilization summary
      "selected_container": "20ft Standard Container",
      "recommended_load_type": "fcl_preferred",
      "total_cbm": 19.41, "total_weight_kg": 2250.0, "total_items": 155,
      "capacity_cbm": 33.2, "safe_capacity_cbm": 28.22, "max_payload_kg": 28200,
      "utilization_percent": 58.46, "risk_level": "high", "risk_score": 6
    },
    "cargo_mix": [ { "item_name": "TVs", "quantity": 50, "dimensions_m": {"length":1.2,"width":0.2,"height":0.8}, "unit_cbm":0.19, "total_cbm":9.6, "unit_weight_kg":12.0, "total_weight_kg":600.0, "stackable": false, "unload_priority": 2, "category_tags": ["fragile","non_stackable"] } ],
    "container_options": [ { "option_name": "20ft Standard Container", "container_count": 1, "total_capacity_cbm": 33.2, "safe_capacity_cbm": 28.22, "payload_limit_kg": 28200, "estimated_utilization_percent": 58.46, "unused_safe_cbm": 8.81, "reason": "Fits within safe CBM and payload limits." } ],
    "zone_layout": [ { "zone_name": "front_floor_base_zone", "description": "...", "items": [ { "item_name": "Scooters", "quantity": 5, "sequence_number": 1, "reason": "..." } ] } ],
    "loading_sequence": [ { "sequence_number": 1, "item_name": "Scooters", "quantity": 5, "suggested_zone": "Bottom floor zone, evenly distributed and secured", "category_tags": ["heavy","non_stackable"], "reason": "..." } ],
    "fit_check": { "status": "fits_selected_container", "selected_container_checked": "20ft Standard Container", "warnings": [], "recommendations": [], "item_fit_results": [] },
    "layout_notes": [],
    "frontend_hints": { "primary_view": "container_utilization", "secondary_view": "zone_layout", "show_cargo_tags": true, "show_fit_warnings": true, "show_loading_sequence": true }
  },

  "executive_summary": {
    "status": "needs_more_information",
    "headline": "Shipment is usable for first-pass planning, but not ready to book yet.",
    "decision": "review_required",
    "ready_for_first_pass": true,
    "ready_for_booking": false,
    "booking_score": 40,
    "next_gate": "fill_missing_information",
    "shipment_snapshot": {},
    "top_strengths": [], "top_risks": [], "top_missing_items": [], "top_next_actions": []
  },

  "ui_sections": [
    { "section_id": "logistics", "title": "Logistics", "status": "review_required",
      "summary": "Logistics plan is usable for first-pass planning but needs review before booking.",
      "metrics": {}, "bullets": [], "actions": [] }
    // ... one card each for: Executive Decision, Shipment Snapshot, Procurement,
    //     Logistics, Compliance & Documents, Costs & Insurance, Partner Checks, Next Actions
  ],

  "booking_readiness": {
    "status": "needs_more_information", "score": 40,
    "ready_for_first_pass": true, "ready_for_booking": false,
    "next_gate": "fill_missing_information",
    "blockers": [], "missing_information": [], "review_items": [], "ready_items": [], "next_steps": []
  },

  "final_answer": {
    "status": "review_required",
    "headline": "This request is usable for first-pass planning, but review is still required.",
    "answer_text": "...", "ready_items": [], "blockers": [], "warnings": [], "next_actions": []
  },

  "action_plan": {
    "status": "review_before_booking",
    "summary": "The plan is usable for first-pass planning, but review is needed before booking.",
    "immediate_actions": [], "before_booking": [], "partner_steps": [], "user_questions": [], "ready_to_continue": []
  },

  "partner_review_status": "partner_review_not_configured",   // or a live status once orchestrator is connected
  "partner_review_summary": null,

  "shopping_quality_review": { "applicable": true, "status": "...", "summary": "...", "selected_items_count": 3, "warnings": [], "blockers": [], "recommendations": [] },
  "procurement_advice": { "applicable": true, "status": "...", "summary": "...", "recommendations": [], "negotiation_points": [], "user_questions": [] },
  "logistics_quality_review": { "applicable": true, "status": "...", "summary": "...", "warnings": [], "blockers": [], "recommendations": [] },
  "document_quality_review": { "applicable": false, "status": "not_applicable", "summary": "...", "warnings": [], "blockers": [], "recommendations": [] },
  "trade_terms_advice": { "applicable": true, "incoterm": null, "origin_country": null, "destination_country": "USA", "warnings": [], "blockers": [], "recommendations": [], "user_questions": [] },
  "insurance_advice": { "applicable": true, "insurance_recommendation": null, "warnings": [], "blockers": [], "recommendations": [] },
  "document_requirements_advice": { "applicable": true, "required_documents": [], "conditional_documents": [], "missing_or_unconfirmed_documents": [], "warnings": [], "recommendations": [], "user_questions": [] },
  "landed_cost_advice": { "applicable": true, "known_inputs": {}, "missing_cost_inputs": [], "blockers": [], "warnings": [], "recommendations": [] },
  "trade_compliance_readiness": { "applicable": true, "ready_for_partner_review": false, "blockers": [], "missing_information": [], "warnings": [], "compliance_flags": [], "recommendations": [], "ready_items": [] },
  "clarification_questions": [ "What is the origin/supplier country?", "..." ],

  "backend_validation": {
    "response_contract_valid": true,
    "response_contract_errors": [],
    "response_contract_warnings": []
  },

  "request_metadata": {
    "request_type": "text",              // "text" | "json_file" | "document_files"
    "input_source": "...",               // echoes back exactly what was passed in
    "include_raw_response": false,
    "served_by": "backend_service"
  }

  // "raw_response": {...}  <- present only if include_raw_response=True
}
```

### 5.5 Recommended render order for any UI consuming this payload

```
1. executive_summary
2. logistics_metrics
3. logistics_visualizer
4. ui_sections
5. booking_readiness
6. final_answer
7. action_plan
8. partner_review_status
9. backend_validation
```

### 5.6 Status/decision vocabulary

- `decision` / top-level verdict: `clear` | `review_required` | `blocked`
- `partner_review_status`: `partner_review_not_configured` (standalone/offline) | live values such as `clear`, `review_required`, `blocked` once the orchestrator is connected
- `backend_validation.response_contract_valid`: should always be `true` in a healthy system — if `false`, the payload is still returned but the UI should show a "backend payload warning"
- Logistics scenario → expected `readiness_status` examples (from README test scenarios): normal dry cargo → `ready_for_review`; hazardous cargo → `critical_review_required`; oversized multi-container → `critical_review_required`; perishable cargo → `review_required`; missing dimensions → `partial_plan_needs_more_information`

### 5.7 Error handling contract

If anything throws inside the pipeline, `backend_service.py` catches it and still returns a **fully-shaped payload** (same top-level keys as §5.4) with:
- `status: "error"`, `decision: "blocked"`
- `final_answer.status: "blocked"`, headline `"Request failed before the agent workflow could complete."`
- `backend_validation.response_contract_valid: false`, with the exception message in `response_contract_errors`
- an additional `error: {type, message, request_type}` field
- every advisory sub-object (`shopping_quality_review`, `procurement_advice`, etc.) present but marked `applicable: false`, `status: "not_applicable"`

This means **a caller never has to special-case a missing field** — the shape is stable whether the request succeeded or failed.

### 5.8 Debugging: `include_raw_response=True`

Passing `include_raw_response=True` to any of the three entry points adds a `raw_response` key containing the full internal User Agent contract (§4). Not intended for production UI rendering — use structured fields (§5.4) instead; raw response is for developers only.

---

## 6. Data files & fixtures worth knowing about

```
data/suppliers/sample_shopping_request.json   — canonical shopping request example
data/scenarios/*.json                          — logistics scenario pack (normal, hazardous, oversized, perishable, missing-dimensions)
data/documents/sample_invoice.txt, sample_packing_list.txt  — document-flow fixtures
config/partner_integrations.example.env        — template for RISK/COMPLIANCE/TRADER MCP names + FINANCE_REST_BASE_URL
config/gemini.example.env                       — template for optional Gemini smart-answer key
```

## 7. Current readiness (from README, as of last update)

| Area | Status |
|---|---|
| User Agent / Router | Working |
| Shopping Agent | Working |
| Logistics Agent | Working |
| Document AI Agent | Working |
| Logistics Visualizer payload | Working |
| Partner Review Service (adapter layer) | Working |
| Trade Orchestrator Adapter | Working |
| Compact Frontend Payload | Working |
| Backend Payload Validation | Working |
| Standalone Demo Mode | Working |
| Live Partner Mode | Partially working — blocked on partner-side Trader Agent needing `OPENAI_API_KEY` (external, not a backend bug) |

The backend is fully usable and demo-ready in **standalone mode** (no partner services running) — it always returns a valid, contract-checked payload; only the final verdict is capped at `review_required` instead of `clear` until live partner checks are wired up.

## 8. How to think about extending this system

- **Add a new specialist agent** (e.g., customs brokerage): create `app/<name>_agent.py` following the `{agent_name, status, summary}` contract, register it in `user_agent.py`'s routing, add its result to `specialist_responses`, and add a corresponding advisor + `ui_sections` card if it should be user-visible.
- **Add a new partner integration**: extend `app/partner_adapters/`, add its config var to `partner_integrations.example.env`, and make sure `partner_review_service.py` treats missing config as `not_configured` (never a hard failure).
- **Change what the frontend sees**: edit `app/frontend_payload.py` / `compact_frontend_payload.py` / `ui_sections_builder.py` — do not change `user_agent.py`'s raw contract casually, since `response_contract_validator.py` enforces it.
- **Never bypass `app/backend_service.py`** from a new frontend — it is the stability boundary between internal agent refactors and external consumers.
