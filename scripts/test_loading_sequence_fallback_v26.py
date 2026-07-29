from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "app" / "backend_service.py"
PLANNING_PATH = ROOT / "frontend" / "src" / "pages" / "ContainerPlanning.jsx"
BACKEND = BACKEND_PATH.read_text(encoding="utf-8-sig")
PLANNING = PLANNING_PATH.read_text(encoding="utf-8-sig")


def fail(message: str) -> None:
    raise AssertionError(message)


def extract_js_function(source: str, name: str) -> str:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", source)
    if not match:
        fail(f"Could not find JavaScript function {name}")

    brace_start = source.find("{", match.end())
    if brace_start < 0:
        fail(f"Could not find opening brace for {name}")

    depth = 0
    in_string = None
    escaped = False

    for index in range(brace_start, len(source)):
        char = source[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
        else:
            if char in {"'", '"', "`"}:
                in_string = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[match.start(): index + 1]

    fail(f"Could not find closing brace for {name}")


# Backend source must create a canonical row for the Phase-2 shipment path.
for required in (
    "def _phase2_v16_loading_step(item):",
    '"loading_sequence": [_phase2_v16_loading_step(item)]',
    '"Padded and secured central loading zone"',
    '"Floor-loaded zone with protected overhead clearance"',
    '"Segregated approved dangerous-goods zone"',
):
    if required not in BACKEND:
        fail(f"Backend loading-sequence contract is missing: {required}")

print("PASS - backend shipment payload creates a structured loading sequence")


# The page must preserve backend rows and derive rows when the array is absent.
for required in (
    "function buildFallbackLoadingSequence(cargoMix)",
    "function resolveLoadingSequence(visualizer)",
    "const loadingSequence = resolveLoadingSequence(lv);",
    "{loadingSequence.map((s) => (",
):
    if required not in PLANNING:
        fail(f"Container Planning fallback is missing: {required}")

if "{(lv.loading_sequence || []).map((s) => (" in PLANNING:
    fail("Container Planning still maps the possibly empty backend array directly")

print("PASS - Container Planning always resolves rows before rendering")


node = shutil.which("node.exe") or shutil.which("node")
if not node:
    fail("Node.js was not found on PATH")

functions = "\n\n".join(
    extract_js_function(PLANNING, name)
    for name in (
        "normalizeLoadingTags",
        "buildFallbackLoadingSequence",
        "resolveLoadingSequence",
    )
)

javascript = f'''
{functions}

const tvFallback = resolveLoadingSequence({{
  cargo_mix: [{{
    item_name: "tvs",
    quantity: 50,
    category_tags: ["fragile"],
    stackable: true,
  }}],
}});

const provided = [{{
  sequence_number: 7,
  item_name: "provided cargo",
  quantity: 3,
  suggested_zone: "Backend zone",
  reason: "Backend reason",
}}];

const preserved = resolveLoadingSequence({{
  loading_sequence: provided,
  cargo_mix: [{{ item_name: "ignored fallback", quantity: 1 }}],
}});

const controls = buildFallbackLoadingSequence([
  {{ item_name: "machinery", quantity: 2, category_tags: ["heavy"] }},
  {{ item_name: "glass", quantity: 4, category_tags: ["non_stackable"] }},
  {{ item_name: "batteries", quantity: 5, category_tags: ["battery"] }},
]);

console.log(JSON.stringify({{ tvFallback, preserved, controls }}));
'''

with tempfile.TemporaryDirectory(prefix="loading_sequence_v26_") as temporary:
    script = Path(temporary) / "test.js"
    script.write_text(javascript, encoding="utf-8")

    completed = subprocess.run(
        [node, str(script)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )

if completed.returncode != 0:
    fail("Node fallback test failed:\n" + completed.stdout)

try:
    result = json.loads(completed.stdout.strip().splitlines()[-1])
except Exception as exc:
    fail(f"Could not parse fallback output: {exc}\n{completed.stdout}")

rows = result["tvFallback"]
if len(rows) != 1:
    fail(f"Expected one TV loading row, got: {rows}")

row = rows[0]
if row.get("item_name") != "tvs" or row.get("quantity") != 50:
    fail(f"TV row identity/quantity is wrong: {row}")

if "Padded and secured" not in row.get("suggested_zone", ""):
    fail(f"TV fallback lacks a padded loading zone: {row}")

reason = row.get("reason", "").lower()
for phrase in ("cushioning", "corner protection", "secure"):
    if phrase not in reason:
        fail(f"TV fallback reason lacks {phrase!r}: {row}")

if result["preserved"] != [{
    "sequence_number": 7,
    "item_name": "provided cargo",
    "quantity": 3,
    "suggested_zone": "Backend zone",
    "reason": "Backend reason",
}]:
    fail("An existing backend loading sequence was not preserved")

zones = [item["suggested_zone"] for item in result["controls"]]
if not any("weight-distribution" in zone for zone in zones):
    fail(f"Heavy control has no low weight-distribution zone: {zones}")
if not any("Floor-loaded" in zone for zone in zones):
    fail(f"Non-stackable control has no floor zone: {zones}")
if not any("dangerous-goods" in zone for zone in zones):
    fail(f"Hazardous control has no segregated zone: {zones}")

print("PASS - one-item TV shipment receives handling guidance")
print("PASS - backend rows are preserved and safety-tag fallbacks are specialized")
