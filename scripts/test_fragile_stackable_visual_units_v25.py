from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "frontend" / "src" / "components" / "Container3DVisualizer.jsx"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8-sig")


def fail(message: str) -> None:
    raise AssertionError(message)


def extract_function(name: str) -> str:
    match = re.search(
        rf"\bfunction\s+{re.escape(name)}\s*\(",
        SOURCE,
    )

    if not match:
        fail(f"Could not find function {name}")

    brace_start = SOURCE.find("{", match.end())
    if brace_start < 0:
        fail(f"Could not find opening brace for function {name}")

    depth = 0
    in_string = None
    escaped = False
    index = brace_start

    while index < len(SOURCE):
        char = SOURCE[index]

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
                    return SOURCE[match.start(): index + 1]

        index += 1

    fail(f"Could not find closing brace for function {name}")


can_stack_source = extract_function("canStack")

for required in (
    "unit.stackable === false",
    "base.stackable === false",
    'hasTag(unit.tags, "hazardous", "battery", "non_stackable")',
    'hasTag(base.tags, "hazardous", "battery", "non_stackable")',
    "if (unit.name === base.name) return true;",
):
    if required not in can_stack_source:
        fail(f"canStack is missing required rule: {required}")

if 'hasTag(base.tags, "hazardous", "battery", "non_stackable", "fragile")' in can_stack_source:
    fail("canStack still treats every fragile base as non-stackable")

if "stackable: unit.stackable" not in SOURCE:
    fail("placed visual boxes do not preserve the authoritative stackable flag")

print("PASS - stackability metadata and safety rules are present")


function_names = [
    "fitOrientation",
    "boxesOverlap",
    "canStack",
    "candidatePositions",
    "tryPlaceUnit",
    "shouldUseAggregatePreview",
    "makeAggregatePreviewUnits",
    "boxInsideContainer",
    "packUnits",
]

functions = "\n\n".join(extract_function(name) for name in function_names)

node = shutil.which("node.exe") or shutil.which("node")
if not node:
    fail("Node.js was not found on PATH")

javascript = f"""
function cleanText(value) {{
  return String(value ?? "").trim().toLowerCase();
}}

function hasTag(tags, ...needles) {{
  const normalized = new Set((tags || []).map((t) => cleanText(t).replaceAll(" ", "_")));
  return needles.some((needle) => normalized.has(cleanText(needle).replaceAll(" ", "_")));
}}

function asNumber(value, fallback = null) {{
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}}

{functions}

function makeUnits(stackable, tags) {{
  return Array.from({{ length: 50 }}, (_, index) => ({{
    name: "tvs",
    quantity: 50,
    copy: index + 1,
    representative: index === 0,
    length_m: 1.2,
    width_m: 0.2,
    height_m: 0.8,
    total_cbm: 9.6,
    unit_cbm: 0.192,
    aggregate_volume_only: false,
    dimensions_are_aggregate: false,
    aggregate_preview: false,
    tags,
    stackable,
    color: "#ffffff",
    dimension_source: "backend dimensions",
    original_index: 0,
  }}));
}}

const container = {{
  length_m: 5.9,
  width_m: 2.35,
  height_m: 2.39,
}};

const fragileStackable = packUnits(
  makeUnits(true, ["fragile", "stackable"]),
  container
);

const explicitlyNonStackable = packUnits(
  makeUnits(false, ["fragile", "non_stackable"]),
  container
);

const hazardous = packUnits(
  makeUnits(true, ["hazardous", "stackable"]),
  container
);

console.log(JSON.stringify({{
  fragileStackable: {{
    boxes: fragileStackable.boxes.length,
    omitted: fragileStackable.omittedCount,
    rejected: fragileStackable.rejectedOutOfBounds,
  }},
  explicitlyNonStackable: {{
    boxes: explicitlyNonStackable.boxes.length,
    omitted: explicitlyNonStackable.omittedCount,
  }},
  hazardous: {{
    boxes: hazardous.boxes.length,
    omitted: hazardous.omittedCount,
  }},
}}));
"""

with tempfile.TemporaryDirectory(prefix="visualizer_v25_") as temporary:
    script_path = Path(temporary) / "packing_test.js"
    script_path.write_text(javascript, encoding="utf-8")

    completed = subprocess.run(
        [node, str(script_path)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )

if completed.returncode != 0:
    fail("Node packing regression failed:\n" + completed.stdout)

try:
    result = json.loads(completed.stdout.strip().splitlines()[-1])
except Exception as exc:
    fail(f"Could not parse Node packing output: {exc}\n{completed.stdout}")

fragile = result["fragileStackable"]

if fragile != {"boxes": 50, "omitted": 0, "rejected": 0}:
    fail(f"Expected all 50 fragile-stackable TVs to fit, got: {fragile}")

if result["explicitlyNonStackable"]["omitted"] <= 0:
    fail("Explicit non-stackable control unexpectedly stacked all 50 units")

if result["hazardous"]["omitted"] <= 0:
    fail("Hazardous control unexpectedly stacked all 50 units")

print("PASS - 50 fragile-stackable TVs produce 50 bounded visual units")
print("PASS - explicit non-stackable and hazardous controls remain protected")
