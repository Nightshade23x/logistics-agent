from __future__ import annotations

import ast
import sys
from pathlib import Path

# V28_TEST_PATH_BOOTSTRAP_V32
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend_service import (
    _frav2_explicit_weight_details_from_prompt,
    _frav2_explicit_weight_from_prompt,
    _frav2_sync_item_weight_v28,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "app" / "backend_service.py"
SOURCE = BACKEND.read_text(encoding="utf-8-sig")


def fail(message: str) -> None:
    raise AssertionError(message)


def close(actual, expected, tolerance=0.001):
    return abs(float(actual) - float(expected)) <= tolerance


ast.parse(SOURCE, filename=str(BACKEND))

if "PER_UNIT_WEIGHT_AUTHORITY_V28" not in SOURCE:
    fail("V28 backend marker is missing")

if "explicit_weight_details" not in SOURCE:
    fail("final response sync is not using explicit weight details")

print("PASS - V28 is wired into final response synchronization")


imperial_prompt = (
    "Ship 10 crates from India to Port of Los Angeles. "
    "Each crate is 4 ft x 3 ft x 2 ft and weighs 220.462 lb. "
    "The crates are fragile and stackable."
)

imperial = _frav2_explicit_weight_details_from_prompt(imperial_prompt)

if not isinstance(imperial, dict) or imperial.get("is_per_unit") is not True:
    fail(f"imperial per-unit semantics were not detected: {imperial}")

if not close(imperial.get("unit_weight_kg"), 100):
    fail(f"imperial unit weight should be 100 kg: {imperial}")

if not close(imperial.get("total_weight_kg"), 1000):
    fail(f"imperial total weight should be 1000 kg: {imperial}")

if not close(imperial.get("quantity"), 10):
    fail(f"imperial quantity should be 10: {imperial}")

if not close(_frav2_explicit_weight_from_prompt(imperial_prompt), 1000):
    fail("legacy total-weight helper did not return the converted shipment total")

print("PASS - 220.462 lb each x 10 converts to 1000 kg total")


metric_prompt = (
    "Ship 10 crates from India to Port of Los Angeles. "
    "Each crate is 1.2192 m x 0.9144 m x 0.6096 m and weighs 100 kg. "
    "The crates are fragile and stackable."
)

metric = _frav2_explicit_weight_details_from_prompt(metric_prompt)

if not isinstance(metric, dict) or metric.get("is_per_unit") is not True:
    fail(f"metric per-unit semantics were not detected after decimal dimensions: {metric}")

if not close(metric.get("unit_weight_kg"), 100):
    fail(f"metric unit weight should be 100 kg: {metric}")

if not close(metric.get("total_weight_kg"), 1000):
    fail(f"metric total weight should be 1000 kg, not 100 kg: {metric}")

print("PASS - decimal dimensions no longer break per-unit metric weight parsing")


item = {
    "item_name": "crates",
    "quantity": 1,
    "total_cbm": 6.796,
    "unit_cbm": 0.6796,
}

quantity = _frav2_sync_item_weight_v28(item, 1000.0, imperial)

if not close(quantity, 10) or item.get("quantity") != 10:
    fail(f"cargo quantity was not restored from the prompt: {item}")

if not close(item.get("unit_weight_kg"), 100):
    fail(f"cargo unit weight is wrong: {item}")

if not close(item.get("total_weight_kg"), 1000):
    fail(f"cargo total weight is wrong: {item}")

if item.get("weight_source") != "explicit_per_unit_weight":
    fail(f"cargo weight source is wrong: {item}")

print("PASS - single cargo row receives quantity, unit weight, and total weight")


total_kg = _frav2_explicit_weight_details_from_prompt(
    "Ship 10 CBM ceramic tiles from India to USA. Total weight is 2200.5 kg."
)

if not close(total_kg.get("total_weight_kg"), 2200.5, tolerance=0.000001):
    fail(f"direct decimal kilograms were changed: {total_kg}")

if total_kg.get("is_per_unit") is not False:
    fail(f"explicit total kilograms were misclassified: {total_kg}")

print("PASS - direct decimal total kilograms remain exact")


total_lb = _frav2_explicit_weight_details_from_prompt(
    "Ship 10 CBM ceramic tiles from India to USA. Total weight is 2204.62 lb."
)

if not close(total_lb.get("total_weight_kg"), 1000):
    fail(f"explicit total pounds did not convert cleanly to 1000 kg: {total_lb}")

if total_lb.get("is_per_unit") is not False:
    fail(f"explicit total pounds were misclassified: {total_lb}")

print("PASS - explicit total pounds remain shipment totals")
