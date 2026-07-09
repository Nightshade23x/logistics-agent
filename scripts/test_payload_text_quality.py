from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BAD_TEXT_PATTERNS = [
    "readyto",
    "catalogitem",
    "haveitems",
    "frompressure",
    "purchaseorders",
    "negotiationbaseline",
    "customsresponsibility",
    "insurancebefore",
    "orcrates",
    "requirements.Run",
    "yet.Partner",
]


def collect_strings(value, path="payload"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from collect_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from collect_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def main() -> None:
    env = os.environ.copy()
    env.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_compact_frontend_payload.py",
            "json",
            "data/suppliers/sample_shopping_request.json",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(result.returncode)

    payload = json.loads(result.stdout)

    failures = []

    for path, text in collect_strings(payload):
        for pattern in BAD_TEXT_PATTERNS:
            if pattern in text:
                failures.append((path, pattern, text))

    if failures:
        print("Found joined-word text issues:")
        for path, pattern, text in failures[:30]:
            print(f"\n- Pattern: {pattern}")
            print(f"  Path: {path}")
            print(f"  Text: {text}")
        raise SystemExit(1)

    print("PASS: no known joined-word text issues found")


if __name__ == "__main__":
    main()
