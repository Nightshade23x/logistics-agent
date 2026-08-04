from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api_server import app

PROMPT = (
    "Calculate landed cost for glass bottles from India to USA using CIF. "
    "Procurement value 15000 USD, freight quote 2200 USD, insurance premium "
    "500 USD, duty rate 6 percent, import tax 7 percent, customs brokerage "
    "300 USD, and local delivery 650 USD."
)


def fail(message, value=None):
    suffix = "" if value is None else "\n" + repr(value)
    raise AssertionError(message + suffix)


with TestClient(app) as client:
    response = client.post(
        "/api/request/text",
        json={"user_text": PROMPT, "include_raw_response": False},
    )

if response.status_code != 200:
    fail(f"HTTP {response.status_code}", response.text)

payload = response.json()
advice = payload.get("landed_cost_advice") or {}
landed = advice.get("estimated_landed_cost_usd")
if landed is None or abs(float(landed) - 21025.34) > 0.01:
    fail("Landed cost changed", advice)

final_answer = payload.get("final_answer") or {}
answer_text = str(final_answer.get("answer_text") or "")
headline = str(final_answer.get("headline") or "")
short_answer = str(payload.get("short_answer") or "")

for label, text in (
    ("headline", headline),
    ("answer_text", answer_text),
    ("short_answer", short_answer),
):
    if "21,025.34" not in text:
        fail(f"{label} does not surface the calculated total", text)

if not answer_text.startswith("Estimated landed cost: $21,025.34"):
    fail("Answer does not lead with the requested calculation", answer_text)

for stale in (
    "Container cannot be selected reliably yet",
    "Add final packed CBM or item dimensions",
    "What is the final packed CBM",
):
    if stale in answer_text:
        fail("Irrelevant logistics-plan guidance remains", answer_text)

if "Calculation breakdown:" not in answer_text:
    fail("Calculation breakdown is missing", answer_text)

print("PASS - landed-cost answer leads with $21,025.34")
print("PASS - irrelevant container guidance is absent")
print("PASS - landed-cost calculation breakdown is shown")

backend_source = (ROOT / "app/backend_service.py").read_text(
    encoding="utf-8-sig", errors="replace"
)
if "LANDED_COST_DIRECT_ANSWER_AUTHORITY_V35" not in backend_source:
    fail("V35 backend marker is missing")

frontend_source = (ROOT / "frontend/src/pages/Dashboard.jsx").read_text(
    encoding="utf-8-sig", errors="replace"
)
if "MISSING_INFO_REQUEST_VISIBILITY_V35" not in frontend_source:
    fail("Missing-information request visibility marker is missing")
if "setText(payload?.request_metadata?.input_source || text);" not in frontend_source:
    fail("Merged backend input source is not copied into the Request textarea")

label_markers = []
for path in (ROOT / "frontend/src").rglob("*"):
    if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx", ".css"}:
        continue
    try:
        source = path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        continue
    if "DEMO_3D_LABEL_NO_TRUNCATION_V35" in source:
        label_markers.append(path)

if len(label_markers) != 1:
    fail("Expected exactly one V35 3D-label marker", label_markers)

label_source = label_markers[0].read_text(
    encoding="utf-8-sig", errors="replace"
)
if "String(text).slice(0, 20)" in label_source:
    fail("3D label still truncates cargo names to 20 characters", label_markers[0])

for expected in (
    'const labelText = String(text || "");',
    "ctx.measureText(labelText).width",
    "ctx.fillText(labelText, 42, 92);",
):
    if expected not in label_source:
        fail(f"3D label fit logic is missing {expected}", label_markers[0])

print("PASS - missing information is copied into the visible request")
print("PASS - 3D cargo labels retain the full cargo name")
