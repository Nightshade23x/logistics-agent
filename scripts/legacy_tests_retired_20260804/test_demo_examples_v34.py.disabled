from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api_server import app

EXAMPLES = [
    {
        "name": "complete ceramic tiles logistics",
        "prompt": "Ship 10 crates of ceramic tiles from India to Germany using CIF. Each crate is 1.2 m x 1.0 m x 0.8 m and weighs 250 kg. The cargo is fragile and stackable.",
        "kind": "logistics",
        "cbm": 9.6,
        "weight": 2500,
        "quantity": 10,
        "destination": "Germany",
    },
    {
        "name": "fragile non-stackable glass pallets",
        "prompt": "Ship 8 pallets of glass jars from India to USA using CIF. Each pallet is 1.2 m x 1.0 m x 1.5 m and weighs 180 kg. The cargo is fragile and non-stackable.",
        "kind": "logistics",
        "cbm": 14.4,
        "weight": 1440,
        "quantity": 8,
        "destination": "USA",
    },
    {
        "name": "complete landed cost",
        "prompt": "Calculate landed cost for glass bottles from India to USA using CIF. Procurement value 15000 USD, freight quote 2200 USD, insurance premium 500 USD, duty rate 6 percent, import tax 7 percent, customs brokerage 300 USD, and local delivery 650 USD.",
        "kind": "landed_cost",
    },
    {
        "name": "lithium battery documents",
        "prompt": "List the required shipping and compliance documents for 20 lithium-ion battery packs sent by air from China to Germany under DDP. Each pack weighs 25 kg.",
        "kind": "documents",
    },
]

MISSING_INITIAL = (
    "Ship 8 pallets of glass jars from India to USA. "
    "Each pallet is 1.2 m x 1.0 m x 1.5 m and weighs 180 kg. "
    "The cargo is fragile."
)
MISSING_ADDITION = (
    "Use CIF. Procurement value is 15000 USD, freight quote is 2200 USD, "
    "insurance premium is 500 USD, duty rate is 6 percent, import tax is "
    "7 percent, customs brokerage is 300 USD, and local delivery is 650 USD."
)
MISSING_COMBINED = MISSING_INITIAL + " Additional information: " + MISSING_ADDITION

FALSE_MESSAGES = {
    "No shipment items were available, so document requirements may be incomplete.",
    "No shipment items were found for compliance review.",
    "logistics review was not applicable.",
}

MISPLACED_RISK_MESSAGES = {
    "Logistics planning output is available for review.",
}


def close(a, b, tolerance=0.01):
    return abs(float(a) - float(b)) <= tolerance


def all_strings(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif isinstance(value, str):
        yield value


def section(payload, section_id):
    for item in payload.get("ui_sections") or []:
        if isinstance(item, dict) and item.get("section_id") == section_id:
            return item
    return None


def request_in_process(prompt):
    with TestClient(app) as client:
        response = client.post(
            "/api/request/text",
            json={"user_text": prompt, "include_raw_response": False},
        )
    if response.status_code != 200:
        raise AssertionError(f"HTTP {response.status_code}: {response.text}")
    return response.json()


def request_live(prompt):
    body = json.dumps(
        {"user_text": prompt, "include_raw_response": False}
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:8000/api/request/text",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode("utf-8"))


def assert_common_consistency(payload):
    snapshot = section(payload, "shipment_snapshot")
    if not isinstance(snapshot, dict):
        raise AssertionError("Shipment Snapshot section is missing")
    if snapshot.get("status") != "ready_for_review":
        raise AssertionError(f"Snapshot status is {snapshot.get('status')!r}")

    strings = set(all_strings(payload))
    stale = sorted(FALSE_MESSAGES & strings)
    if stale:
        raise AssertionError(f"Stale false messages remain: {stale}")

    executive = payload.get("executive_summary") or {}
    top_risks = {
        str(value).strip()
        for value in (executive.get("top_risks") or [])
    }
    misplaced = sorted(MISPLACED_RISK_MESSAGES & top_risks)
    if misplaced:
        raise AssertionError(
            f"Positive logistics messages remain under Main Risks: {misplaced}"
        )

    executive_section = section(payload, "executive_decision") or {}
    executive_bullets = {
        str(value).strip()
        for value in (executive_section.get("bullets") or [])
    }
    misplaced = sorted(MISPLACED_RISK_MESSAGES & executive_bullets)
    if misplaced:
        raise AssertionError(
            f"Positive logistics messages remain in Executive Decision risks: {misplaced}"
        )

    bullets = snapshot.get("bullets") or []
    if any(str(value).strip().endswith(": None") for value in bullets):
        raise AssertionError(f"Snapshot still displays None: {bullets}")

    executive = payload.get("executive_summary") or {}
    if not executive.get("top_strengths"):
        raise AssertionError("Executive strengths remain empty")


def assert_logistics(payload, spec):
    if payload.get("detected_intent") != "logistics":
        raise AssertionError(f"Intent is {payload.get('detected_intent')!r}")
    if "logistics_agent" not in (payload.get("agents_called") or []):
        raise AssertionError("logistics_agent was not recorded")

    metrics = payload.get("logistics_metrics") or {}
    if not close(metrics.get("total_cbm"), spec["cbm"]):
        raise AssertionError(f"CBM mismatch: {metrics}")
    if not close(metrics.get("total_weight_kg"), spec["weight"]):
        raise AssertionError(f"Weight mismatch: {metrics}")

    visualizer = payload.get("logistics_visualizer") or {}
    rows = visualizer.get("cargo_mix") or []
    quantity = sum(int(float(row.get("quantity") or 0)) for row in rows if isinstance(row, dict))
    if quantity != spec["quantity"]:
        raise AssertionError(f"Quantity mismatch: {rows}")

    destination = str(payload.get("destination_country") or payload.get("destination") or "")
    if spec["destination"].lower() not in destination.lower():
        raise AssertionError(f"Destination mismatch: {destination!r}")

    assert_common_consistency(payload)


def assert_landed_cost(payload):
    advice = payload.get("landed_cost_advice") or {}
    if not advice.get("applicable"):
        raise AssertionError(f"Landed cost advice is not applicable: {advice}")
    if advice.get("status") == "blocked":
        raise AssertionError(f"Landed cost is blocked: {advice}")
    missing = advice.get("missing_cost_inputs") or []
    if missing:
        raise AssertionError(f"Complete example still has missing costs: {missing}")
    if advice.get("blockers"):
        raise AssertionError(f"Complete example still has blockers: {advice}")

    landed = advice.get("estimated_landed_cost_usd")
    if landed is None:
        raise AssertionError(f"No landed-cost estimate was calculated: {advice}")
    if not close(landed, 21025.34):
        raise AssertionError(f"Unexpected landed cost: {advice}")

    subtotal = advice.get("estimated_subtotal_known_usd")
    if subtotal is None or not close(subtotal, landed):
        raise AssertionError(f"Landed-cost summary is inconsistent: {advice}")


def assert_documents(payload):
    advice = payload.get("document_requirements_advice") or {}
    if not advice.get("applicable"):
        raise AssertionError(f"Document advice is not applicable: {advice}")
    required = {str(value).lower() for value in advice.get("required_documents") or []}
    for expected in ("commercial invoice", "packing list"):
        if expected not in required:
            raise AssertionError(f"Required document missing: {expected}; got {required}")
    trade = payload.get("trade_terms_advice") or {}
    if str(trade.get("incoterm") or "").upper() != "DDP":
        raise AssertionError(f"DDP was not preserved: {trade}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--open-report", action="store_true")
    args = parser.parse_args()

    request_fn = request_live if args.live else request_in_process
    mode = "live API" if args.live else "in-process FastAPI"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = ROOT / "test_outputs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"demo_examples_v34_{stamp}.txt"
    payload_path = report_dir / f"demo_examples_v34_payloads_{stamp}.json"

    payloads = {}
    lines = [f"DEMO EXAMPLES V34 - {mode}", "=" * 100]
    failures = []

    for spec in EXAMPLES:
        try:
            payload = request_fn(spec["prompt"])
            payloads[spec["name"]] = payload
            if spec["kind"] == "logistics":
                assert_logistics(payload, spec)
            elif spec["kind"] == "landed_cost":
                assert_landed_cost(payload)
            elif spec["kind"] == "documents":
                assert_documents(payload)
            lines.append(f"PASS - {spec['name']}")
        except Exception as exc:
            failures.append(spec["name"])
            lines.append(f"FAIL - {spec['name']}: {exc}")

    try:
        initial = request_fn(MISSING_INITIAL)
        combined = request_fn(MISSING_COMBINED)
        payloads["missing_info_initial"] = initial
        payloads["missing_info_combined"] = combined

        initial_metrics = initial.get("logistics_metrics") or {}
        combined_metrics = combined.get("logistics_metrics") or {}
        for metrics, label in ((initial_metrics, "initial"), (combined_metrics, "combined")):
            if not close(metrics.get("total_cbm"), 14.4):
                raise AssertionError(f"{label} CBM changed: {metrics}")
            if not close(metrics.get("total_weight_kg"), 1440):
                raise AssertionError(f"{label} weight changed: {metrics}")

        initial_trade = initial.get("trade_terms_advice") or {}
        if initial_trade.get("status") != "needs_more_information":
            raise AssertionError(f"Initial prompt did not request missing trade terms: {initial_trade}")

        combined_trade = combined.get("trade_terms_advice") or {}
        if str(combined_trade.get("incoterm") or "").upper() != "CIF":
            raise AssertionError(f"Added CIF was not applied: {combined_trade}")

        assert_landed_cost(combined)
        assert_common_consistency(combined)
        lines.append("PASS - missing-information completion preserves shipment and applies new details")
    except Exception as exc:
        failures.append("missing-information flow")
        lines.append(f"FAIL - missing-information flow: {exc}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload_path.write_text(json.dumps(payloads, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("\n".join(lines))
    print(f"Report: {report_path}")
    print(f"Payloads: {payload_path}")

    if args.open_report and sys.platform.startswith("win"):
        import subprocess
        subprocess.Popen(["notepad.exe", str(report_path)])

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
