from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "app" / "backend_service.py"
SOURCE = BACKEND.read_text(encoding="utf-8-sig")


def fail(message: str) -> None:
    raise AssertionError(message)


ast.parse(SOURCE, filename=str(BACKEND))

for score in (4, 5):
    stale = f'return "moderate", {score}, "ready_for_review_with_high_risk"'
    if stale in SOURCE:
        fail(f"stale contradictory readiness remains for moderate risk score {score}")

    expected = f'return "moderate", {score}, "ready_for_review"'
    if expected not in SOURCE:
        fail(f"canonical moderate readiness is missing for risk score {score}")

print("PASS - moderate-risk shipments use ready_for_review")

pattern = re.compile(
    r'"fit_check"\s*:\s*\{\s*'
    r'"status"\s*:\s*container\["fit_status"\]\s*,\s*'
    r'"selected_container_checked"\s*:\s*container\["selected_container"\]',
    flags=re.DOTALL,
)

if not pattern.search(SOURCE):
    fail("fit_check does not inherit container['selected_container']")

print("PASS - fit check identifies the selected container")

for fragment in (
    'return "critical", 10, "not_ready_blockers_found"',
    'return "high", 9, "not_ready_blockers_found"',
    'return "high", 8, "not_ready_blockers_found"',
):
    if fragment not in SOURCE:
        fail(f"hazardous-risk behavior changed unexpectedly: {fragment}")

print("PASS - hazardous high/critical readiness remains blocked")
