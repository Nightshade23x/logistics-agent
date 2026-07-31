# Changelog

## 2026-07-31 — Consultant handover candidate

### Added

- React/Vite application frontend.
- FastAPI application integration.
- Free-text and guided shipment workflows.
- Synchronized request persistence until explicit clearing.
- Shopping and supplier-selection workflows.
- Deterministic CBM, weight, load-type, and container calculations.
- 3D container-loading visualizer.
- Container utilization and remaining-capacity metrics.
- Dynamic route and gateway guidance.
- Landlocked-origin inland pre-carriage handling.
- Trade-agreement and origin-document guidance.
- Dynamic shipping-document and compliance sections.
- Landed-cost workflow.
- Compact serpentine shipment-process flowchart.
- Focused regression scripts.
- Updated README and handover documentation.

### Improved

- Negated hazardous-cargo interpretation.
- Shared dimension-unit parsing.
- Explicit port preservation.
- Automatically selected gateway handling.
- CBM terminology in the frontend.
- Blank startup behaviour in a new tab.
- Synchronization between free-text and guided input.
- Dynamic flow direction and decision-diamond readability.
- Handling guidance for ordinary non-fragile and non-hazardous cargo.

### Security and repository hygiene

- Added `.env.example`.
- Expanded `.gitignore`.
- Added security guidance.
- Added Pull Request validation checklist.
- Documented public-repository secret handling.

### Known limitations

- Routes are indicative rather than live.
- Preferential eligibility requires HS-code and rules-of-origin confirmation.
- External partner-agent availability is optional.
- Production deployment, authentication, monitoring, and persistent storage are not included.
