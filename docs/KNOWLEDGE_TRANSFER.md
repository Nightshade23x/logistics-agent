# Logistics Multi-Agent System – Knowledge Transfer

## 1. Purpose

This document transfers the technical knowledge required to run, understand, demonstrate, maintain, test, and extend the Logistics Multi-Agent System.

The application accepts a natural-language shipment request and transforms it into a structured logistics plan. It combines deterministic Python logic, optional LLM interpretation, specialist-agent handoffs, compliance/document enrichment, and a React frontend with a 3D container visualiser.

The most important design principle is that **deterministic backend logic is authoritative for calculations and structured fields**. An LLM may help interpret wording, but it should not silently override values such as CBM, weight, container selection, utilisation, or structured shipment status.

---

## 2. Main Capabilities

The current system can:

- interpret shipment requests written in natural language;
- extract item names, quantities, dimensions, weights, routes and cargo properties;
- normalise common units such as metres, centimetres, feet, inches, kilograms, pounds, litres and CBM;
- calculate unit and total CBM;
- calculate shipment weight;
- identify fragile, hazardous, radioactive, perishable and non-stackable cargo;
- recommend FCL or LCL;
- recommend a suitable container;
- check container capacity and payload;
- generate packaging and loading recommendations;
- assess logistics risk and readiness;
- provide route/gateway planning information;
- enrich responses with compliance and document guidance;
- preserve useful user-facing units while using standard internal units;
- expose structured agent handoff data;
- build frontend-ready JSON;
- display a 3D container visualisation;
- display shipment process-flow information;
- run locally with LLM interpretation disabled.

---

## 3. Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- deterministic logistics modules
- optional LLM interpretation
- local JSON reference data

### Frontend

- React
- Vite
- JavaScript / JSX
- structured API response rendering
- 3D container visualisation

### Development

- Git / GitHub
- PowerShell
- Python regression tests
- frontend production build checks

---

## 4. High-Level Architecture

```text
User
  |
  v
React Frontend
  |
  v
FastAPI (api_server.py)
  |
  v
Request Interpreter / Router
  |
  v
Deterministic Backend
  |
  +--> Logistics Agent
  |      +--> unit normalisation
  |      +--> CBM / weight
  |      +--> cargo classification
  |      +--> FCL / LCL
  |      +--> container strategy
  |      +--> loading / packaging
  |      +--> risk / readiness
  |
  +--> Route / Gateway Logic
  +--> Compliance Enrichment
  +--> Document Requirements
  +--> Specialist-Agent Handoffs
  |
  v
Frontend Response Cleanup
  |
  v
Structured JSON
  |
  v
React UI / 3D Container Visualiser
```

The frontend should render structured response fields rather than recalculate logistics values from prose.

---

## 5. Important Repository Files

```text
logistics-agent/
├── api_server.py
├── Start-Logistics-App.ps1
├── app/
│   ├── backend_service.py
│   ├── llm_request_interpreter.py
│   ├── logistics_agent.py
│   ├── document_agent.py
│   ├── dynamic_compliance_enrichment.py
│   ├── frontend_response_cleanup.py
│   ├── practical_imperial_precision_v80.py
│   ├── unit_converter.py
│   ├── container_fit.py
│   ├── container_strategy.py
│   ├── shipping_load_advisor.py
│   ├── loading_planner.py
│   ├── packaging_advisor.py
│   ├── logistics_risk.py
│   ├── readiness_checklist.py
│   └── route_advisor.py
├── data/
│   └── dynamic_compliance_reference_v65.json
├── docs/
│   ├── agent_contract.md
│   └── architecture.md
├── frontend/
│   └── src/components/Container3DVisualizer.jsx
├── scripts/
│   ├── test_*.py
│   └── legacy_tests_retired_20260804/
├── backups/
├── patch_logs/
└── test_outputs/
```

`backups`, `patch_logs`, and `test_outputs` are local development artefacts rather than core application source code.

---

## 6. Starting the Application

The repository is currently located at:

```text
E:\Projects 2026\logistics-agent
```

The simplest launcher is:

```powershell
cd "E:\Projects 2026\logistics-agent"
powershell -ExecutionPolicy Bypass -File .\Start-Logistics-App.ps1
```

The path is machine-specific. If the repository is moved again, avoid hard-coded absolute paths in the launcher where possible.

### Backend only

```powershell
cd "E:\Projects 2026\logistics-agent"
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```

Typical backend URL:

```text
http://127.0.0.1:8000
```

### Frontend only

```powershell
cd "E:\Projects 2026\logistics-agent\frontend"
npm install
npm run dev
```

Typical Vite URL:

```text
http://localhost:5173
```

---

## 7. `api_server.py`

This file defines the FastAPI application and exposes backend functionality to the frontend.

### `request_text`

The main request endpoint is:

```text
POST /api/request/text
```

Its responsibilities are to:

1. receive the user's natural-language shipment request;
2. validate the request body;
3. call the backend processing pipeline;
4. return the complete structured JSON response.

Conceptually:

```text
Frontend -> request_text() -> backend_service.process_text_request() -> JSON
```

### Final response middleware

The API also contains final-response cleanup logic. This exists because different internal paths may produce equivalent values with slightly different representations. The final API layer ensures the response returned to the frontend remains consistent.

A practical weight authority also prevents floating-point conversion residue such as `999.998811 kg` from being exposed when an imperial value such as `2204.62 lb` clearly represents a practical `1000 kg` shipment.

---

## 8. `app/backend_service.py`

This is the central backend orchestration file.

The key function is the **last active definition** of:

```python
process_text_request(...)
```

It coordinates:

- request interpretation;
- intent detection;
- cargo parsing;
- unit normalisation;
- logistics-plan generation;
- route/gateway logic;
- compliance enrichment;
- document requirements;
- specialist-agent handoffs;
- frontend response construction;
- final answer construction;
- compatibility and regression guards.

There are historical wrappers with the same function name. When debugging, inspect the **final active definition**, because later wrappers may call earlier versions internally.

---

## 9. `app/llm_request_interpreter.py`

The important function is:

```python
run_backend_with_interpreter(...)
```

The system is designed to be deterministic-first.

```text
User text
   |
   v
Deterministic backend
   |
   +--> sufficient / parseable --> continue
   |
   +--> ambiguous --> optional LLM interpretation
```

The LLM is an interpretation aid, not the source of authoritative logistics calculations.

For repeatable local testing/demo operation:

```powershell
$env:LLM_INTERPRETER_MODE = "off"
```

---

## 10. `app/logistics_agent.py`

This contains the core shipment-planning logic.

### `CargoItem`

Represents cargo with fields such as:

- name;
- quantity;
- dimensions;
- weight;
- fragile;
- perishable;
- hazardous;
- radioactive;
- stackable;
- unload priority.

### `unit_cbm`

Calculates one item's cubic volume:

```text
length × width × height
```

### `total_cbm`

Calculates:

```text
unit CBM × quantity
```

### `total_weight_kg`

Calculates:

```text
unit weight × quantity
```

### `validate_item`

Rejects invalid cargo such as non-positive quantity, invalid dimensions or negative weight before planning continues.

### `calculate_total_cbm`

Validates items and sums their CBM.

### `calculate_total_weight`

Validates items and sums shipment weight.

### `classify_cargo`

Identifies handling categories such as fragile, hazardous, radioactive, perishable, non-stackable and general cargo.

### `recommend_container`

Compares shipment volume and weight against configured container capacities/payload limits to select an appropriate option.

### `build_logistics_plan`

This is the main Logistics Agent planning function. It normalises cargo, creates cargo objects, calculates totals, classifies cargo, checks fit, recommends FCL/LCL and container strategy, builds loading/packaging advice, assesses risk/readiness, and returns a structured logistics plan.

---

## 11. FCL / LCL Recommendation

The backend decides whether a shipment is more suitable for:

- **FCL** – Full Container Load;
- **LCL** – Less than Container Load.

The recommendation can consider:

- total CBM;
- total weight;
- fragility;
- stackability;
- cargo characteristics;
- expected container utilisation;
- shipment practicality.

The output is explainable and can include recommendation, confidence, reasons, warnings, recommendations, and decision inputs.

---

## 12. Container Recommendation

Configured container examples include:

### 20ft Standard

```text
Capacity: approximately 33.2 CBM
Maximum payload: approximately 28,200 kg
```

### 40ft Standard

```text
Capacity: approximately 67.7 CBM
Maximum payload: approximately 26,700 kg
```

### 40ft High Cube

```text
Capacity: approximately 76.4 CBM
```

The recommendation should consider both volume and payload, not CBM alone.

---

## 13. Supporting Logistics Modules

### `app/unit_converter.py`

Normalises common dimensions, weights and volume units into standard internal values.

Internal planning generally uses:

```text
metres + kilograms + CBM
```

while user-facing values can preserve the units originally entered.

### `app/container_fit.py`

Checks whether cargo can fit within container volume and payload limits.

### `app/container_strategy.py`

Compares container options and selects a practical container arrangement.

### `app/shipping_load_advisor.py`

Contains FCL/LCL decision logic.

### `app/loading_planner.py`

Creates a suggested loading sequence based on cargo properties and practical handling.

### `app/packaging_advisor.py`

Generates cargo-specific packaging/handling recommendations such as `Fragile`, `This Side Up`, and `Do Not Stack`.

### `app/logistics_risk.py`

Produces logistics risk status, risk score, blockers, warnings and recommendations.

### `app/readiness_checklist.py`

Checks whether the shipment has enough information to proceed or whether additional details/review are required.

### `app/route_advisor.py`

Provides indicative route/gateway recommendations. These are planning recommendations and not guaranteed real-time carrier routes.

---

## 14. Aggregate vs Per-Unit Weight

The backend distinguishes between:

```text
Each item weighs 20 kg
```

and:

```text
The total shipment weighs 2000 kg
```

For explicit total weights, the payload can mark:

```text
weight_source = "explicit_total"
```

The consistency rule is:

```text
unit_weight_kg = total_weight_kg / quantity
```

This prevents the unit-weight and total-weight fields from contradicting each other.

---

## 15. `app/practical_imperial_precision_v80.py`

This module handles practical imperial-to-metric precision.

Example:

```text
2204.62 lb -> 999.998811 kg
```

For a user this is clearly intended as approximately:

```text
1000 kg
```

The module therefore:

1. detects relevant imperial measurements;
2. calculates the exact metric conversion;
3. determines whether the value is close enough to a practical whole-kilogram value;
4. updates matching structured fields only;
5. preserves the original user-facing imperial value;
6. synchronises answer text.

This is deliberately narrow and does **not** blindly round every weight.

---

## 16. `app/frontend_response_cleanup.py`

This is the final transformation layer between backend logic and React rendering.

The important function is the final active:

```python
cleanup_frontend_response(...)
```

Its responsibilities include:

- synchronising logistics metrics;
- maintaining handoff data;
- preserving route fields;
- generating/normalising the frontend visualiser payload;
- preserving display units;
- attaching compliance/document information;
- ensuring final answers and structured fields remain consistent.

Important display-unit helpers include logic around:

```text
_final_weight_v71
_final_volume_v71
_final_sync_weight_v71
_final_sync_volume_v71
```

The principle is:

```text
Internal calculations = standard metric values
Frontend display = preserve useful user-entered units where possible
```

---

## 17. 3D Container Visualiser

The main frontend component is:

```text
frontend/src/components/Container3DVisualizer.jsx
```

It renders structured backend data rather than calculating logistics itself.

It can display:

- selected container;
- cargo blocks;
- cargo labels;
- cargo quantities;
- used CBM;
- remaining CBM;
- utilisation percentage;
- loading zones;
- fit warnings;
- loading sequence.

The main data flow is:

```text
Logistics calculations
        |
        v
logistics_visualizer JSON
        |
        v
frontend_response_cleanup.py
        |
        v
Container3DVisualizer.jsx
        |
        v
3D display
```

A previous aggregate/direct-volume duplicate-rendering issue was fixed and regression-tested.

---

## 18. `app/dynamic_compliance_enrichment.py`

The main entry point is:

```python
enrich_dynamic_compliance_payload(...)
```

This layer uses the shipment context to add structured compliance guidance based on origin, destination and cargo characteristics.

It can add:

- status;
- summary;
- blockers;
- warnings;
- recommendations;
- licences/permits;
- approvals;
- required documents;
- conditional documents;
- trade-agreement information.

It can also identify special requirements related to lithium batteries, dangerous goods, radioactive cargo, dual-use cargo and sensitive routes.

---

## 19. Compliance Reference Data

Reference rules are stored in:

```text
data/dynamic_compliance_reference_v65.json
```

Separating reference data from Python makes the rules easier to review and extend.

Important limitation: this is not a live legal, tariff, customs or sanctions database. Official information must be verified before a real shipment is booked.

---

## 20. Document Agent

### `app/document_agent.py`

The Document AI Agent is responsible for trade/shipping document processing, including:

- document extraction;
- document type recognition;
- document validation;
- invoice vs packing-list comparison;
- mismatch detection;
- document-set completeness;
- structured handoffs to other agents.

Typical documents include:

- commercial invoice;
- packing list;
- bill of lading;
- certificate of origin.

The Document Agent should not perform container-loading calculations; that belongs to the Logistics Agent.

---

## 21. Specialist Agent Responsibilities

### Logistics Agent

- shipment planning;
- CBM and weight;
- FCL/LCL;
- container recommendation;
- packaging;
- loading;
- logistics risk/readiness;
- logistics handoff.

### Document Agent

- document extraction;
- validation;
- comparison;
- completeness;
- document handoff.

### Finance Agent

- freight cost;
- insurance;
- budget;
- financial risk.

### Trader Agent

- HS codes;
- duties;
- Incoterms;
- trade agreements;
- export strategy.

### Compliance Agent

- allowed/restricted/prohibited checks;
- licences;
- permits;
- hazardous-material requirements;
- country controls.

### Risk Agent

- broader country/trade risk;
- sanctions-related risk information.

The frontend is **not** an agent. It collects input and renders outputs.

---

## 22. Agent Contract and Handoffs

The shared contract is documented in:

```text
docs/agent_contract.md
```

It exists so separately developed agents can exchange compatible structured data.

A Logistics Agent handoff can include fields such as:

```json
{
  "total_cbm": "...",
  "total_weight_kg": "...",
  "container_recommendation": "...",
  "origin": "...",
  "destination": "...",
  "risk_level": "...",
  "cargo_categories": "..."
}
```

Each specialist agent should keep its responsibility separate rather than silently performing another agent's job.

---

## 23. Important Response Sections

Depending on the request, the backend may return sections such as:

```text
logistics_metrics
logistics_visualizer
logistics_quality_review
handoff_payload
trade_compliance_readiness
trade_agreement_advice
document_requirements_advice
request_metadata
final_answer
display_answer
frontend_answer
```

The frontend should prefer these structured fields instead of scraping values from answer text.

---

## 24. Testing Strategy

Active regression tests are stored as:

```text
scripts/test_*.py
```

They cover areas such as:

- logistics calculations;
- cargo parsing;
- request interpretation;
- FCL/LCL;
- container selection;
- container visualisation;
- unit conversion;
- imperial precision;
- non-positive quantity handling;
- compliance;
- route/port selection;
- frontend payload consistency;
- FastAPI responses;
- document flows.

Important regression tests include:

```text
scripts/test_final_weight_authority_v32.py
scripts/test_canonical_total_weight_line_v82.py
scripts/test_practical_imperial_precision_v80.py
scripts/test_practical_imperial_text_sync_v81.py
scripts/test_explicit_imperial_total_precision_v79.py
scripts/test_nonpositive_quantity_weight_guard_v77.py
scripts/test_direct_volume_visual_dedupe_v76.py
```

These tests represent real bugs/edge cases discovered during development.

---

## 25. Running Tests

From the repository root:

```powershell
cd "E:\Projects 2026\logistics-agent"
$env:LLM_INTERPRETER_MODE = "off"
$env:PYTHONPATH = (Get-Location).Path
```

Run one test:

```powershell
python scripts\test_final_weight_authority_v32.py
```

Run maintained standalone tests:

```powershell
Get-ChildItem .\scripts\test_*.py |
  Sort-Object Name |
  ForEach-Object {
    Write-Host "`nRunning $($_.Name)..."
    python $_.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Test failed: $($_.Name)"
    }
  }
```

Frontend build check:

```powershell
cd frontend
npm run build
```

A Browserslist warning alone is not a build failure; use the command exit code as the success criterion.

---

## 26. Retired Historical Tests

Some superseded tests were moved to:

```text
scripts/legacy_tests_retired_20260804/
```

They were preserved rather than permanently deleted. They represent older response contracts and were removed from active discovery so outdated expectations do not conflict with the current implementation.

---

## 27. Environment and Secrets

Important environment variables include:

```text
PYTHONPATH
LLM_INTERPRETER_MODE
```

Optional LLM integrations may use provider-specific API keys.

**Never commit API keys to GitHub.**

Recommended ignored items include:

```text
.env
.env.*
__pycache__/
*.pyc
node_modules/
patch_logs/
test_outputs/
backups/
```

according to team repository policy.

---

## 28. Git Workflow

Typical feature-branch workflow:

```powershell
git checkout main
git pull origin main
git checkout -b feature-name
```

After development/testing:

```powershell
git status
git add <specific files>
git commit -m "Description of change"
git push -u origin feature-name
```

Then merge through a pull request or an agreed team merge process.

Do not merge unverified changes into `main`.

---

## 29. Simple Demo Prompt

Use this to show that the full application works:

```text
Ship 20 boxes from Mumbai, India to Hamburg, Germany. Each box is 1 m × 0.5 m × 0.5 m and weighs 30 kg. Recommend the container and shipping plan.
```

The basic expected calculations are:

```text
Unit CBM = 1 × 0.5 × 0.5 = 0.25 CBM
Total CBM = 0.25 × 20 = 5 CBM
Total weight = 30 × 20 = 600 kg
```

The resulting UI should demonstrate parsing, metrics, load/container recommendation and the container visualiser.

---

## 30. Recommended Technical Walkthrough

### 1. `api_server.py`

Show `request_text`.

Explain: the frontend request enters the backend through FastAPI here.

### 2. `app/backend_service.py`

Show the final `process_text_request`.

Explain: this is the main orchestration layer.

### 3. `app/llm_request_interpreter.py`

Show `run_backend_with_interpreter`.

Explain: the deterministic backend remains authoritative and the LLM is optional.

### 4. `app/logistics_agent.py`

Show:

```text
CargoItem
calculate_total_cbm
calculate_total_weight
classify_cargo
recommend_container
build_logistics_plan
```

Explain: this is the main logistics planning logic.

### 5. `app/dynamic_compliance_enrichment.py`

Show `enrich_dynamic_compliance_payload`.

Explain: it adds route/country/cargo-specific compliance and document guidance.

### 6. `app/frontend_response_cleanup.py`

Show the final `cleanup_frontend_response`.

Explain: it prepares one consistent payload for React.

### 7. `frontend/src/components/Container3DVisualizer.jsx`

Explain: it renders backend-provided container/cargo data and utilisation.

### 8. One regression test

Show a passing test such as `test_final_weight_authority_v32.py` to demonstrate end-to-end consistency checking.

---

## 31. Important Design Decisions

### Deterministic calculations are authoritative

CBM, weight, utilisation, cargo quantity and container selection should come from structured deterministic logic.

### Structured payloads drive the frontend

The UI should not parse critical values back out of generated answer text.

### Optional AI must fail safely

The basic application should remain usable with LLM interpretation disabled.

### Missing/unsafe information should be visible

Use statuses such as:

```text
review_required
needs_more_information
blocked
```

instead of fabricating certainty.

### Agent responsibilities remain separate

Logistics, Finance, Compliance, Trader, Risk and Document responsibilities should remain distinguishable and communicate through structured handoffs.

---

## 32. Current Limitations

### Compliance

Local/static compliance reference data is guidance only and should be verified against current authoritative sources for real shipments.

### Routing

Gateway and route suggestions are indicative and may not reflect real-time carrier schedules or availability.

### Freight pricing

Real freight prices require current external carrier/forwarder data.

### Container visualisation

The 3D visualiser is a planning aid, not professional load-engineering certification.

### Natural-language requests

Ambiguous or incomplete requests may still require clarification or a review status.

---

## 33. Suggested Future Improvements

Potential improvements include:

- live carrier/freight rates;
- real-time vessel schedules;
- official customs/tariff APIs;
- sanctions API integration;
- richer HS-code classification;
- live insurance quotations;
- real routing/distance services;
- advanced 3D packing optimisation;
- authentication;
- persistent shipment history/database;
- production deployment;
- monitoring/logging;
- deeper integration tests;
- refactoring large orchestration files into smaller services.

---

## 34. Troubleshooting

### Backend does not start

```powershell
python --version
python -m py_compile api_server.py
```

Ensure the repository root is on `PYTHONPATH`.

### Frontend does not start

```powershell
cd frontend
npm install
npm run dev
```

### Frontend cannot reach backend

Confirm the API is running on:

```text
http://127.0.0.1:8000
```

### Unexpected LLM/API-provider problems

```powershell
$env:LLM_INTERPRETER_MODE = "off"
```

The deterministic workflow should still function.

### Launcher points to an old repository path

Inspect `Start-Logistics-App.ps1` for hard-coded paths. The repository was moved from the old C: location to:

```text
E:\Projects 2026\logistics-agent
```

Prefer repository-relative path discovery in future launcher updates.

---

## 35. Handover Checklist

A developer taking over the project should understand:

- [ ] how to create/activate the Python environment;
- [ ] how to install frontend dependencies;
- [ ] how to start backend and frontend;
- [ ] `api_server.py` and the text API route;
- [ ] the final `process_text_request` orchestration path;
- [ ] deterministic-first interpretation;
- [ ] Logistics Agent CBM/weight calculations;
- [ ] cargo classification;
- [ ] FCL/LCL logic;
- [ ] container recommendation and fit;
- [ ] loading and packaging recommendations;
- [ ] risk and readiness checks;
- [ ] route/gateway guidance;
- [ ] dynamic compliance enrichment;
- [ ] Document Agent responsibilities;
- [ ] agent contract and handoff fields;
- [ ] frontend response cleanup;
- [ ] display-unit preservation;
- [ ] practical imperial precision logic;
- [ ] 3D container visualiser data flow;
- [ ] active regression tests;
- [ ] frontend build verification;
- [ ] development-only folders;
- [ ] current compliance/routing limitations.

---

## 36. Key Files Summary

| File | Responsibility |
|---|---|
| `api_server.py` | FastAPI endpoints and final API response handling |
| `app/backend_service.py` | Main backend orchestration |
| `app/llm_request_interpreter.py` | Natural-language interpretation / deterministic-first execution |
| `app/logistics_agent.py` | Core logistics calculations and shipment planning |
| `app/unit_converter.py` | Measurement normalisation |
| `app/container_fit.py` | Container fit/capacity checks |
| `app/container_strategy.py` | Container strategy |
| `app/shipping_load_advisor.py` | FCL/LCL recommendation |
| `app/loading_planner.py` | Loading sequence |
| `app/packaging_advisor.py` | Packaging recommendations |
| `app/logistics_risk.py` | Logistics risk assessment |
| `app/readiness_checklist.py` | Shipment readiness checks |
| `app/route_advisor.py` | Route/gateway planning |
| `app/document_agent.py` | Document extraction/validation |
| `app/dynamic_compliance_enrichment.py` | Compliance/document enrichment |
| `app/frontend_response_cleanup.py` | Final frontend-compatible payload |
| `app/practical_imperial_precision_v80.py` | Imperial/metric precision consistency |
| `data/dynamic_compliance_reference_v65.json` | Local compliance reference data |
| `docs/agent_contract.md` | Shared specialist-agent contract |
| `frontend/src/components/Container3DVisualizer.jsx` | 3D container visualisation |
| `scripts/test_*.py` | Active regression tests |

---

## 37. Final System Flow

```text
USER
 |
 v
REACT FRONTEND
 |
 | POST /api/request/text
 v
FASTAPI
 |
 v
REQUEST INTERPRETER
 |
 v
DETERMINISTIC BACKEND
 |
 +--> unit normalisation
 +--> cargo parsing
 +--> Logistics Agent
 |      +--> CBM
 |      +--> weight
 |      +--> classification
 |      +--> FCL/LCL
 |      +--> container
 |      +--> loading
 |      +--> packaging
 |      +--> risk
 |      +--> readiness
 +--> route/gateway logic
 +--> compliance enrichment
 +--> document requirements
 +--> agent handoffs
 |
 v
FRONTEND RESPONSE CLEANUP
 |
 +--> structured metrics
 +--> display units
 +--> container visualiser payload
 +--> process flow
 +--> final answer
 |
 v
FASTAPI JSON RESPONSE
 |
 v
REACT FRONTEND
 |
 +--> shipment summary
 +--> container recommendation
 +--> 3D container visualiser
 +--> compliance/documents
 +--> process flow
 |
 v
USER
```

---

## 38. Final Notes

The purpose of the system is not simply to generate shipping prose. It transforms an unstructured shipment request into a **structured, explainable and reusable logistics-planning payload**.

The key maintenance principles are:

1. keep logistics calculations deterministic;
2. preserve clear specialist-agent responsibilities;
3. drive the frontend from structured fields;
4. preserve user-entered display units where practical;
5. expose uncertainty and unsafe scenarios clearly;
6. keep regression tests for discovered edge cases;
7. ensure optional integrations fail safely;
8. update this KT document whenever the API contract, core planning flow, major agent responsibility, or frontend response structure changes.
