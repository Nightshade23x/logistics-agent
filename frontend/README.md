# Meridian Logistics — Cargo Operations Console

A Vite + React frontend for the `logistics-agent-avishi-frontend-on-partner-integration`
Python backend, styled to match the reference operations-console design
(`file.html`), and split into routed pages.

## Architecture

```
frontend/          <- this Vite/React app (what you're reading now)
../api_server.py   <- thin FastAPI wrapper around app/backend_service.py
                       and individual agent modules (added for this UI;
                       does not modify any existing agent logic)
```

The Python backend (`app/backend_service.py`) exposed only plain Python
functions, no HTTP layer. `api_server.py` adds one.

## Running it

**1. Start the backend API** (from the repo root, one directory up from `frontend/`):

```bash
pip install -r requirements.txt
uvicorn api_server:app --reload --port 8000
```

**2. Start the frontend** (from this `frontend/` directory):

```bash
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api/*` to
`http://127.0.0.1:8000` (see `vite.config.js`), so no CORS setup or env
vars are needed in development.

For a production build: `npm run build` (outputs to `frontend/dist/`),
served by any static host, pointed at your deployed `api_server.py`.

## API surface used by this frontend

Full pipeline (recommended path — mirrors `app/backend_service.py`):
- `POST /api/request/text` — free text → full enriched payload
- `POST /api/request/json` — structured shopping/logistics JSON → full enriched payload
- `POST /api/request/documents` — multipart file upload (invoice, packing list, etc.) → full enriched payload

Individual specialist agents (used by the "Partner Agents" / "Procurement"
playgrounds, and by any future integration that wants to call one agent
without running the whole pipeline):
- `POST /api/agents/logistics` — `app/logistics_agent.py::build_logistics_plan`
- `POST /api/agents/shopping` — `app/shopping_agent.py::build_shopping_plan`
- `POST /api/agents/document` — `app/document_service.py::run_document_agent_from_text`
- `POST /api/agents/partner-review` — `app/partner_review_service.py::run_partner_review`
- `POST /api/agents/intent` — `app/agent_router.py::detect_text_intent`

## Pages

| Route | Purpose |
|---|---|
| `/` Dashboard | Request builder (text / structured JSON / document upload) + recent request history |
| `/shipments` | Executive summary + every `ui_sections` card + backend validation |
| `/container-planning` | `logistics_visualizer`: container fit, cargo mix, loading sequence, options, fit check |
| `/procurement` | Shopping quality review, procurement advice, + Shopping Agent playground |
| `/compliance` | Document/trade-terms/insurance/landed-cost/compliance advisors + clarification questions |
| `/partner-agents` | Live partner-review status (Risk/Compliance/Trader/Finance) + raw agent-call playground |
| `/reports` | Final answer, action plan, booking readiness, JSON export |

Because the backend's `ui_sections` and advisor objects are already
self-describing (`{status, summary, metrics, bullets, actions}` /
`{applicable, status, summary, ...lists}`), most of the UI is rendered by
two generic components (`SectionCard`, `AdvisorCard`) rather than
hand-built per field — new backend fields show up automatically.

## State

The last pipeline result and a rolling history of the last 25 requests are
kept in `localStorage` via `src/store.jsx` (a small React context), so a
refresh doesn't lose your last run.
