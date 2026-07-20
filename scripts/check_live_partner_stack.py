from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


FINANCE_HEALTH_URL = "http://127.0.0.1:8003/health"
ORCHESTRATOR_HEALTH_URL = "http://127.0.0.1:8010/health"
ORCHESTRATOR_URL = "http://127.0.0.1:8010/orchestrate"

TEST_QUERY = (
    "ship 50 TVs, 5 Scooters and 100 Ceramic tiles from India to USA. "
    "origin country is India. destination country is USA. country_to is USA. "
    "cargo value is 12730 USD. weight is 2250 kg. volume is 19.41 m3."
)


def request_json_or_text(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 25,
) -> tuple[bool, Any]:
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")

            try:
                return True, json.loads(body)
            except json.JSONDecodeError:
                return True, body.strip()

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}: {body[:500]}"

    except Exception as exc:
        return False, str(exc)


def print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def summarize_agent_statuses(response: Any) -> dict[str, str]:
    statuses: dict[str, str] = {}

    if not isinstance(response, dict):
        return statuses

    possible_agent_sources = [
        response.get("agent_responses"),
        response.get("agents"),
        response.get("results"),
        response.get("raw_report", {}).get("agent_responses")
        if isinstance(response.get("raw_report"), dict)
        else None,
    ]

    for source in possible_agent_sources:
        if not isinstance(source, dict):
            continue

        for agent_name, agent_response in source.items():
            if isinstance(agent_response, dict):
                status = (
                    agent_response.get("status")
                    or agent_response.get("decision")
                    or agent_response.get("result_status")
                    or "present"
                )
                statuses[str(agent_name)] = str(status)
            elif isinstance(agent_response, list):
                statuses[str(agent_name)] = f"list[{len(agent_response)}]"
            else:
                statuses[str(agent_name)] = type(agent_response).__name__

    errors = response.get("agent_errors")

    if isinstance(errors, dict):
        for agent_name, error in errors.items():
            statuses[str(agent_name)] = f"FAILED: {str(error)[:160]}"

    return statuses


def main() -> None:
    print("LIVE PARTNER STACK CHECK")
    print("========================")
    print("This script checks optional live partner services.")
    print("It is OK if this fails while Avishi's stack is not running.")

    print_section("Finance Agent")
    finance_ok, finance_response = request_json_or_text(FINANCE_HEALTH_URL)

    if finance_ok:
        print(f"Finance health: OK")
        print(f"Response: {finance_response}")
    else:
        if "404" in str(finance_response) or "Not Found" in str(finance_response):
            print(f"Finance health: UNREACHABLE (endpoint mismatch, not necessarily offline)")
        else:
            print(f"Finance health: OFFLINE / FAILED")
        print(f"Reason: {finance_response}")

    print_section("Trade Orchestrator")
    orchestrator_ok, orchestrator_health = request_json_or_text(ORCHESTRATOR_HEALTH_URL)

    if orchestrator_ok:
        print("Orchestrator health: OK")
        print(f"Response: {orchestrator_health}")
    else:
        if "404" in str(orchestrator_health) or "Not Found" in str(orchestrator_health):
            print(f"Orchestrator health: UNREACHABLE (endpoint mismatch, not necessarily offline)")
        else:
            print("Orchestrator health: OFFLINE / FAILED")
        print(f"Reason: {orchestrator_health}")

    print_section("Direct Orchestrator Review")

    if not orchestrator_ok:
        print("Skipped direct orchestrator call because orchestrator health is not OK.")
        print()
        print("RESULT: PARTNER STACK NOT READY")
        return

    review_ok, review_response = request_json_or_text(
        ORCHESTRATOR_URL,
        method="POST",
        payload={"query": TEST_QUERY},
        timeout_seconds=60,
    )

    if not review_ok:
        print("Direct orchestrator call: FAILED")
        print(f"Reason: {review_response}")
        print()
        print("RESULT: PARTNER STACK NOT READY")
        return

    print("Direct orchestrator call: OK")

    if isinstance(review_response, dict):
        verdict = (
            review_response.get("verdict")
            or review_response.get("status")
            or review_response.get("decision")
            or review_response.get("final_verdict")
        )
        summary = review_response.get("summary") or review_response.get("synthesis")

        print(f"Verdict/status: {verdict}")

        if summary:
            print(f"Summary: {str(summary)[:500]}")

        agent_statuses = summarize_agent_statuses(review_response)

        if agent_statuses:
            print()
            print("Agent statuses:")

            for agent_name, status in sorted(agent_statuses.items()):
                print(f"- {agent_name}: {status}")
        else:
            print()
            print("Agent statuses: not found in response shape")

        response_text = json.dumps(review_response, indent=2, ensure_ascii=True)

        if "OPENAI_API_KEY" in response_text:
            print()
            print("Detected OPENAI_API_KEY error in response.")
            print("Trader Agent likely still needs partner-side OpenAI setup.")

        if "trader_agent" in response_text.lower() and "FAILED" in response_text.upper():
            print()
            print("Detected trader_agent failure in response.")

    else:
        print(f"Raw response: {review_response}")

    print()
    print("RESULT: LIVE PARTNER CHECK COMPLETE")


if __name__ == "__main__":
    main()
