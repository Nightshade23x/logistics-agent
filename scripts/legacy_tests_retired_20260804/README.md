# Retired legacy tests

These checks are preserved for historical reference but are
not part of the maintained test suite. They use the
`.py.disabled` suffix so pytest and the standalone runner do
not collect them.

They were retired only after newer focused tests covered the
maintained behavior or the asserted product behavior was
intentionally replaced.

## Retired files

- `test_api_final_response_cleanup.py` — Superseded by current frontend cleanup, landed-cost input, V71 unit-authority, and API payload tests; it asserts an older cost-field shape.
- `test_avishi_hazardous_container_prompt.py` — Retired because it expects hazardous cargo to be marked immediately available; the current safer behavior correctly requires dangerous-goods review.
- `test_backend_consistency_v3.py` — Superseded historical consistency snapshot; exact agent lists and stale text expectations no longer match the current orchestrator.
- `test_backend_consistency_v6.py` — Superseded historical consistency snapshot; exact agent lists and answer wording are no longer the current contract.
- `test_backend_consistency_v8.py` — Superseded historical consistency snapshot; later V44, V49, V59, V65, V66, V71 and current scenario tests cover the maintained behavior.
- `test_backend_export_regressions.py` — Tests an older exported answer format and string wording; current export-pack and frontend payload tests are the maintained checks.
- `test_backend_payload_polish.py` — Superseded payload-polish snapshot with stale-message wording assumptions covered by later cleanup and compliance-sync tests.
- `test_backend_response_polish_v2.py` — Superseded V2 response-polish snapshot.
- `test_cargo_name_weight_precision_v22.py` — Superseded by V32, V71, V79 and V80 precision tests and current cargo schema semantics.
- `test_completed_landed_cost_answer_v36.py` — Superseded direct-answer wording check; current landed-cost calculations and structured frontend sections are tested separately.
- `test_container_planning_multi_item_consistency.py` — Older aggregate multi-item schema check superseded by the maintained multi-item parser and V47 robustness tests.
- `test_demo_answers_and_ui_v35.py` — Superseded headline wording snapshot; the current UI uses structured sections and a separate Process Flow page.
- `test_demo_examples_v34.py` — Superseded demo status snapshot that predates the current review-required safety model.
- `test_empty_state_simple_tabs_v38.py` — Retired because prompt persistence is now intentional; the test requires the draft to start blank.
- `test_final_demo_bundle_export.py` — Legacy static-demo bundle check; the maintained frontend is the React build.
- `test_frontend_persistence_docs_cbm_v61.py` — Superseded source-string snapshot; current unit-aware KPI and V71 tests cover display behavior.
- `test_full_pipeline_route_precedence.py` — Incorrectly treats preserved raw input fields as normalized route fields; current route-cleanup and V59/V60/V64 tests cover route authority.
- `test_json_regression_v11.py` — Large historical snapshot superseded by focused current regression tests with safer missing-data behavior.
- `test_shopping_demo_regression.py` — Legacy shopping-demo composite; the current procurement, shopping-agent, and shopping-quality tests pass independently, and this project demo is shipping-focused.
- `test_static_frontend_demo_export.py` — Legacy static HTML label snapshot; the maintained frontend is the React application build.

## Still maintained

The maintained suite continues to include the current
backend, API, parser, route, compliance, unit, visualizer,
partner-contract and frontend tests in `scripts/test_*.py`.
