from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.backend_service as backend_service
from fastapi.testclient import TestClient
from api_server import app


SOURCE_PATH = ROOT / "app" / "backend_service.py"
RUN_ALL_PATH = ROOT / "scripts" / "run_all_tests.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8-sig")
RUN_ALL_SOURCE = RUN_ALL_PATH.read_text(encoding="utf-8-sig")


def fail(message: str, detail=None) -> None:
    suffix = "" if detail is None else "\n" + repr(detail)
    raise AssertionError(message + suffix)


def pretty(value) -> str:
    number = float(value)
    if abs(number - round(number)) <= 1e-9:
        return str(int(round(number)))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def assert_payload(payload, expected_total, expected_quantity, expected_unit):
    metrics = payload.get("logistics_metrics") or {}
    visualizer = payload.get("logistics_visualizer") or {}
    container = visualizer.get("container") or {}
    cargo_mix = visualizer.get("cargo_mix") or []
    handoff = payload.get("handoff_payload") or {}
    executive = payload.get("executive_summary") or {}
    snapshot = executive.get("shipment_snapshot") or {}

    if metrics.get("total_weight_kg") != expected_total:
        fail("logistics_metrics total weight mismatch", metrics)
    if container.get("total_weight_kg") != expected_total:
        fail("visualizer container total weight mismatch", container)
    if handoff.get("total_weight_kg") != expected_total:
        fail("handoff total weight mismatch", handoff)
    if snapshot.get("total_weight_kg") != expected_total:
        fail("snapshot total weight mismatch", snapshot)
    if len(cargo_mix) != 1:
        fail("expected one cargo row", cargo_mix)

    item = cargo_mix[0]
    if item.get("quantity") != expected_quantity:
        fail("cargo quantity mismatch", item)
    if item.get("unit_weight_kg") != expected_unit:
        fail("cargo unit weight mismatch", item)
    if item.get("total_weight_kg") != expected_total:
        fail("cargo total weight mismatch", item)

    expected_line = f"- Total weight: {pretty(expected_total)} kg"
    answer = str((payload.get("final_answer") or {}).get("answer_text") or "")
    display = str(payload.get("display_answer") or "")
    frontend = str(payload.get("frontend_answer") or "")

    for label, text in (
        ("final_answer", answer),
        ("display_answer", display),
        ("frontend_answer", frontend),
    ):
        if expected_line not in text:
            fail(f"{label} weight line was not synchronized", text)
        if "- Total weight: not confirmed" in text:
            fail(f"{label} retained an unknown weight", text)


ast.parse(SOURCE, filename=str(SOURCE_PATH))

for marker in (
    "FINAL_WEIGHT_AUTHORITY_V32",
    "_process_text_request_before_final_weight_v32",
    "_v32_rewrite_all_strings",
):
    if marker not in SOURCE:
        fail(f"missing V32 marker: {marker}")

if "scripts/test_phase2_imperial_weight_runtime_v29.py" in RUN_ALL_SOURCE:
    fail("stale V29 test registration remains in run_all_tests.py")

sample = {"nested": {"answer": "Cargo:\n- Total weight: 100 kg\n"}}
backend_service._v32_rewrite_all_strings(sample, 1000)
if "- Total weight: 1000 kg" not in sample["nested"]["answer"]:
    fail("recursive string rewrite helper failed", sample)
print("PASS - recursive answer-text rewrite works")

imperial_prompt = (
    "Ship 10 crates from India to Port of Los Angeles. "
    "Each crate is 4 ft x 3 ft x 2 ft and weighs 220.462 lb. "
    "The crates are fragile and stackable."
)

metric_prompt = (
    "Ship 10 crates from India to Port of Los Angeles. "
    "Each crate is 1.2192 m x 0.9144 m x 0.6096 m and weighs 100 kg. "
    "The crates are fragile and stackable."
)

for prompt, label in (
    (imperial_prompt, "imperial per-unit"),
    (metric_prompt, "metric per-unit"),
):
    direct = backend_service.process_text_request(prompt, include_raw_response=False)
    assert_payload(direct, 1000, 10, 100)
    print(f"PASS - direct backend {label} prompt returns 1000 kg everywhere")

client = TestClient(app)
response = client.post(
    "/api/request/text",
    json={"user_text": imperial_prompt, "include_raw_response": False},
)
if response.status_code != 200:
    fail("FastAPI request failed", response.text)
assert_payload(response.json(), 1000, 10, 100)
print("PASS - FastAPI imperial prompt returns 1000 kg everywhere")

kg_total_prompt = (
    "Ship 10 CBM of ceramic tiles from India to USA. "
    "Total weight is 2200.5 kg."
)
kg_authority = backend_service._v32_authority(kg_total_prompt, {})
if not isinstance(kg_authority, dict) or kg_authority.get("source") != "explicit_total":
    fail("aggregate-volume total prompt was not parsed as an explicit total", kg_authority)
if kg_authority.get("quantity") is not None:
    fail("aggregate-volume number was incorrectly parsed as item quantity", kg_authority)

kg_total = backend_service.process_text_request(kg_total_prompt, include_raw_response=False)
assert_payload(kg_total, 2200.5, 1, 2200.5)
print("PASS - 10 CBM remains one aggregate row with a 2200.5 kg shipment total")

lb_total_prompt = (
    "Ship 10 CBM of ceramic tiles from India to USA. "
    "Total weight is 2204.62 lb."
)
lb_total = backend_service.process_text_request(lb_total_prompt, include_raw_response=False)
assert_payload(lb_total, 1000, 1, 1000)
print("PASS - aggregate 2204.62 lb total converts to 1000 kg without changing quantity")
