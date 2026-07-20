from pathlib import Path
import json
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "demo_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SAMPLE_REQUEST = ROOT / "data" / "suppliers" / "sample_shopping_request.json"
OUTPUT_FILE = OUTPUT_DIR / "standalone_compact_payload.json"

def run_command(command):
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=True,
    )

    if result.returncode != 0:
        print("COMMAND FAILED:")
        print(command)
        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)

    return result.stdout

def main():
    os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    output = run_command(
        f'python scripts\\run_compact_frontend_payload.py json "{SAMPLE_REQUEST}"'
    )

    OUTPUT_FILE.write_text(output, encoding="utf-8")
    payload = json.loads(output)

    validation = payload.get("backend_validation", {})
    executive_summary = payload.get("executive_summary", {})
    booking_readiness = payload.get("booking_readiness", {})

    print("\nDEMO CHECK: standalone backend mode")
    print("----------------------------------")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Top-level status: {payload.get('status')}")
    print(f"Decision: {payload.get('decision')}")
    print(f"Detected intent: {payload.get('detected_intent')}")
    print(f"Agents called: {', '.join(payload.get('agents_called', []))}")
    print(f"Partner review status: {payload.get('partner_review_status')}")
    print(f"Contract valid: {validation.get('response_contract_valid')}")
    print(f"Booking status: {booking_readiness.get('status')}")
    print(f"Ready for first pass: {booking_readiness.get('ready_for_first_pass')}")
    print(f"Ready for booking: {booking_readiness.get('ready_for_booking')}")
    print(f"Booking score: {booking_readiness.get('score')}")
    print(f"UI sections: {len(payload.get('ui_sections', []))}")
    print(f"Executive headline: {executive_summary.get('headline')}")

    errors = validation.get("response_contract_errors", [])
    warnings = validation.get("response_contract_warnings", [])

    if errors:
        print("\nContract errors:")
        for error in errors:
            print(f"- {error}")

    if warnings:
        print("\nContract warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if (
        payload.get("partner_review_status") == "partner_review_not_configured"
        and validation.get("response_contract_valid") is True
    ):
        print("\nRESULT: PASS ")
        print("Standalone backend demo works without live partner services.")
    else:
        print("\nRESULT: CHECK NEEDED ")

if __name__ == "__main__":
    main()
