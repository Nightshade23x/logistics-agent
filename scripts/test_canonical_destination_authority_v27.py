from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend_service import _canonical_route_value_v27, _sync_canonical_route_v27

SOURCE = (ROOT / "app" / "backend_service.py").read_text(encoding="utf-8-sig")
ast.parse(SOURCE)
assert "CANONICAL_ROUTE_AUTHORITY_V27" in SOURCE
assert "payload = _sync_canonical_route_v27(" in SOURCE

payload = {"trade_terms_advice": {
    "origin_country": "India",
    "destination_country": "USA Total weight is 28201 kg",
}}
raw = {"origin_country": "India", "destination_country": "USA"}
fixed = _sync_canonical_route_v27(payload, raw)
assert fixed["trade_terms_advice"]["destination_country"] == "USA"
print("PASS - polluted destination is replaced by canonical USA")

for destination in ("New York, USA", "Port of Los Angeles", "Washington, D.C., USA"):
    payload = {"trade_terms_advice": {
        "origin_country": "India",
        "destination_country": destination + " Total weight is 1200 kg",
    }}
    raw = {"origin_country": "India", "destination_country": destination}
    fixed = _sync_canonical_route_v27(payload, raw)
    assert fixed["trade_terms_advice"]["destination_country"] == destination
print("PASS - valid multi-word destinations are preserved")

nested = {"handoff_payload": {"destination": "Port of Rotterdam"}}
assert _canonical_route_value_v27(nested, "destination_country", "destination") == "Port of Rotterdam"
print("PASS - nested canonical route fields remain supported")

payload = {"trade_terms_advice": {"destination_country": "USA"}}
assert _sync_canonical_route_v27(payload, {})["trade_terms_advice"]["destination_country"] == "USA"
print("PASS - no-canonical fallback is unchanged")
