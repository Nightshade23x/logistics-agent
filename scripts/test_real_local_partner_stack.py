from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


FINANCE_HEALTH_URL = "http://127.0.0.1:8003/health"
ORCHESTRATOR_HEALTH_URL = "http://127.0.0.1:8010/health"
ORCHESTRATOR_URL = "http://127.0.0.1:8010/orchestrate"

TEST_QUERY = (
    "ship 100 Ceramic tiles from India to USA. "
    "origin country is India. country_from is India. "
    "destination country is USA. country_to is USA. "
    "target market is USA. incoterm is CIF. "
    "cargo value is 480.0 USD. weight is 1200.0 kg. volume is 2.88 m3."
)


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def service_available(url: str) -> bool:
    try:
        get_json(url)
        return True
    except Exception:
        return False


def main() -> None:
    finance_up = service_available(FINANCE_HEALTH_URL)
    orchestrator_up = service_available(ORCHESTRATOR_HEALTH_URL)

    if not finance_up or not orchestrator_up:
        print("SKIPPED: local partner stack is not fully running.")
        print(f"Finance health available: {finance_up}")
        print(f"Orchestrator health available: {orchestrator_up}")
        print()
        print("Start Finance on port 8003 and Orchestrator on port 8010, then rerun.")
        return

    finance_health = get_json(FINANCE_HEALTH_URL)
    orchestrator_health = get_json(ORCHESTRATOR_HEALTH_URL)

    response = post_json(ORCHESTRATOR_URL, {"query": TEST_QUERY})

    summary = {
        "finance_health": finance_health,
        "orchestrator_health": orchestrator_health,
        "request_id": response.get("request_id"),
        "parsed_shipment": response.get("parsed_shipment"),
        "has_compliance_report": bool(response.get("compliance_report")),
        "has_trader_report": bool(response.get("trader_report")),
        "has_finance_report": bool(response.get("finance_report")),
        "has_risk_report": bool(response.get("risk_report")),
        "agent_errors": response.get("agent_errors"),
        "verdict": response.get("verdict"),
    }

    print(json.dumps(summary, indent=2, default=str))

    assert finance_health.get("status") == "ok", "Finance health did not return status=ok."
    assert orchestrator_health.get("status") == "ok", "Orchestrator health did not return status=ok."

    parsed = response.get("parsed_shipment") or {}
    assert parsed.get("product_description") == "Ceramic tiles", "Product was not parsed correctly."
    assert parsed.get("country_from") == "India", "Origin country was not parsed correctly."
    assert parsed.get("country_to") == "USA", "Destination country was not parsed correctly."

    assert response.get("finance_report"), "Finance report is missing."
    assert response.get("risk_report"), "Risk report is missing."
    assert response.get("compliance_report"), "Compliance report is missing."
    assert response.get("trader_report"), "Trader report is missing."

    agent_errors = response.get("agent_errors") or {}
    assert not agent_errors, f"Expected no agent_errors, got: {agent_errors}"

    verdict = response.get("verdict") or {}
    assert verdict.get("status") in {"clear", "review_required", "blocked"}, (
        f"Unexpected verdict status: {verdict.get('status')}"
    )

    print()
    print("REAL LOCAL PARTNER STACK CHECK PASSED")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"HTTP error: {exc.code} {exc.reason}")
        print(exc.read().decode("utf-8", errors="replace"))
        sys.exit(1)
