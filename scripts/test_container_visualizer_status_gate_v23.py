from pathlib import Path
import re


SOURCE = Path("frontend/src/components/Container3DVisualizer.jsx")
text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")

match = re.search(
    r"export function hasContainer3DData\(result\) \{(?P<body>.*?)\n\}",
    text,
    flags=re.DOTALL,
)

if not match:
    raise AssertionError("hasContainer3DData() was not found")

body = match.group("body")

if 'result.status === "needs_more_information"' in body:
    raise AssertionError(
        "The visualizer is still blocked solely because the overall response needs more information"
    )

required = [
    "visualizer?.cargo_mix",
    'visualizer?.status !== "unavailable"',
    "Array.isArray(cargoMix)",
]

missing = [token for token in required if token not in body]
if missing:
    raise AssertionError(f"Missing visualizer availability checks: {missing}")

print("PASS - needs_more_information no longer suppresses valid container visualizer data")
print("PASS - unavailable visualizers remain blocked")
print("PASS - cargo_mix is still required")
