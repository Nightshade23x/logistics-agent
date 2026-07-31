# Demo Runbook

## Purpose

This runbook provides a repeatable demonstration sequence for the Logistics Agent application.

It is intended for mentors, consultants, reviewers, and future developers who need to verify the main workflows quickly.

## Before the demo

### 1. Confirm the correct branch

```powershell
git branch --show-current
git status
```

The worktree should be clean before the final handover demonstration.

### 2. Rotate exposed credentials

Rotate any API key that has appeared in:

- screenshots;
- terminal output;
- logs;
- generated reports;
- Git history.

Do not place real values in `.env.example`.

### 3. Build the frontend

```powershell
cd frontend
npm run build
cd ..
```

The build must pass before the demo.

### 4. Run the final focused tests

```powershell
$env:PYTHONPATH = (Get-Location).Path

python scripts/test_dynamic_process_flow_v62.py
python scripts/test_compact_flow_board_v62.py
python scripts/test_serpentine_flow_board_v62.py
python scripts/test_compact_synced_input_flow_v62.py
python scripts/test_blank_entry_fullwidth_flow_v62.py
python scripts/test_frontend_persistence_docs_cbm_v61.py
```

### 5. Start the application

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-Logistics-App.ps1
```

After startup, press `Ctrl+F5` in the browser.

### 6. Confirm a clean session

Open the application in a new browser tab.

The request area should start blank in the new tab.

## Recommended demo sequence

## 1. Ordinary shipment

Submit a complete non-hazardous shipment request.

Show:

- extracted shipment details;
- total CBM and weight;
- FCL/LCL suitability;
- recommended container;
- utilization and remaining capacity;
- indicative route and gateway plan;
- trade-agreement and origin-document guidance;
- required shipping documents;
- dynamic shipment-process flowchart.

## 2. Free-text and guided-input synchronization

Start in the free-text mode.

Switch to the guided workflow and confirm that:

- the shipment request is not erased;
- the same request remains available;
- editing is explicit;
- switching modes does not silently restart the workflow.

## 3. 3D container visualizer

Open the container-planning page.

Show:

- the selected container type;
- cargo blocks;
- cargo volume;
- container capacity;
- utilization percentage;
- remaining CBM;
- fit and loading guidance.

Explain that the visualization is a planning aid rather than a certified loading plan.

## 4. Landlocked-origin shipment

Use a shipment from a landlocked origin such as Zambia.

Show:

- inland pre-carriage;
- reference export gateway;
- ocean corridor;
- destination gateway;
- final delivery;
- route assumptions.

Explain that the route is indicative and does not include live congestion or disruption data.

## 5. Dangerous-goods shipment

Use a hazardous-cargo example such as lithium-ion batteries.

Show:

- hazardous classification;
- specialist review status;
- dangerous-goods documents;
- packaging and handling requirements;
- insurance review;
- carrier-acceptance checks;
- additional steps in the process flow.

## 6. Landed-cost workflow

Use a request containing:

- cargo value;
- freight;
- insurance;
- brokerage;
- local delivery;
- duty rate;
- import tax.

Show the completed calculation.

Then remove one or more commercial inputs and show how the application identifies missing information instead of pretending the calculation is complete.

## 7. Incomplete shipment request

Submit a short request such as:

```text
I need to ship furniture to Germany.
```

Show that the application requests missing dimensions, quantity, weight, origin, delivery terms, or commercial information as needed.

## Suggested talking points

- Deterministic calculations remain authoritative.
- Optional model interpretation helps understand user wording.
- Structured backend fields drive the frontend.
- The application still works in standalone mode.
- Optional partner services can be connected when available.
- Routes, trade guidance, and compliance output are clearly scoped.

## Claims to avoid

Do not claim that:

- a route is currently open;
- a port or canal has no disruption;
- a carrier will definitely accept the cargo;
- preferential duty treatment is guaranteed;
- a shipment is legally compliant solely because the app says so;
- the 3D plan is a certified stowage plan;
- the application replaces a customs broker, lawyer, insurer, or dangerous-goods specialist.

## If an optional service fails

Continue with the standalone demonstration.

State clearly that:

- the optional integration is unavailable;
- deterministic logistics output remains available;
- the application has degraded safely;
- live specialist output was not used.

## After the demo

1. Record mentor and consultant feedback.
2. Create GitHub issues for follow-up work.
3. Review the final feature-branch diff.
4. Push the feature branch.
5. Open a Pull Request into `main`.
6. Merge only after review.
7. Pull the merged `main` branch locally.
8. Tag the mentor-approved handover commit.
