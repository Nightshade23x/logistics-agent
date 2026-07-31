# Consultant Handover

## Project status

The Logistics Agent application is ready for local demonstration and consultant review.

The handover candidate includes:

- a React/Vite frontend;
- a FastAPI backend;
- deterministic logistics calculations;
- synchronized free-text and guided input;
- shopping, logistics, document, trade, compliance, finance, and risk modules;
- a 3D container-loading visualizer;
- route and gateway guidance;
- landed-cost analysis;
- a dynamic serpentine shipment-process flow;
- focused regression scripts.

## Repository workflow

The recommended handover workflow is:

1. complete work on the feature branch;
2. run the final build and regression checks;
3. review the public repository for secrets;
4. push the feature branch;
5. open a Pull Request into `main`;
6. review the changed files;
7. merge after approval;
8. pull the updated `main` branch locally;
9. tag the mentor-approved handover commit.

## Local startup

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-Logistics-App.ps1
```

More detail is available in:

- `README.md`
- `docs/local_setup.md`
- `docs/demo_runbook.md`
- `docs/demo_prompts.md`
- `docs/architecture.md`

## Main components ready for review

### Frontend

- free-text shipment input;
- guided shipment input;
- synchronized request state;
- dashboard and report views;
- compliance and document sections;
- container-planning page;
- 3D loading visualizer;
- dynamic process flow.

### Backend

- request parsing and routing;
- unit normalization;
- CBM and weight calculations;
- FCL/LCL suitability;
- container recommendations;
- route and gateway enrichment;
- trade-agreement and origin-document guidance;
- document and compliance readiness;
- landed-cost calculations;
- structured frontend payload assembly.

### Optional partner services

Risk, Compliance, Trader, and Finance services can be connected through the partner orchestrator.

The core standalone application must not depend on those services being available.

## Consultant review priorities

The consultant should review:

1. repository and module boundaries;
2. backend and frontend API contracts;
3. schema validation;
4. secret and environment management;
5. dependency pinning;
6. error handling and logging;
7. automated test organization;
8. CI/CD and branch protection;
9. production deployment architecture;
10. authentication and authorization;
11. data-source ownership and update policy;
12. vulnerability and dependency scanning.

## Known limitations

- The current application is designed primarily for local demonstration.
- No production deployment is included.
- Route plans are indicative and do not use live carrier schedules by default.
- Live port closures, congestion, weather, sanctions, and maritime advisories are not connected by default.
- Trade-agreement existence does not prove product eligibility.
- Preferential treatment requires correct HS classification, rules of origin, and accepted proof of origin.
- Container visualizations are planning aids and not certified loading plans.
- Optional partner-agent availability may vary.
- Production authentication, monitoring, and persistent storage require further work.
- No repository license has yet been selected.

## Security handover

Before giving access to external reviewers:

- rotate any API key exposed in screenshots, logs, terminals, or Git history;
- ensure `.env` is not tracked;
- ensure generated folders are ignored;
- remove confidential customer or shipment documents;
- review public commit history for secrets;
- confirm `.env.example` contains names only and no values.

## Final handover checklist

- [ ] Frontend production build passes
- [ ] Final focused regressions pass
- [ ] `git diff --check` passes
- [ ] Repository hygiene check passes
- [ ] No credentials are committed
- [ ] Feature branch is pushed
- [ ] Pull Request is reviewed
- [ ] Changes are merged into `main`
- [ ] Local `main` is updated
- [ ] Mentor approves the final handover
- [ ] Approved commit is tagged
