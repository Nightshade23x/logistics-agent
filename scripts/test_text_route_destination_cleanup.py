from __future__ import annotations

import json
import os


def main() -> None:
    os.environ["USE_TRAINED_ROUTER"] = "1"
    os.environ["ENABLE_TRADER_AGENT"] = "1"
    os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    from app.user_agent import run_user_agent_from_text

    prompt = (
        "estimate freight and find supplier for 100 ceramic tiles from India to USA. "
        "Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. "
        "Duty rate is 5 percent. Import tax rate is 8 percent."
    )

    response = run_user_agent_from_text(prompt)

    specialist_responses = response.get("specialist_responses") or {}
    logistics_response = specialist_responses.get("logistics_agent") or {}
    logistics_handoff = logistics_response.get("handoff_payload") or {}
    logistics_report = logistics_response.get("report") or ""
    final_answer = response.get("final_answer") or ""
    missing_information = response.get("missing_information") or []

    summary = {
        "status": response.get("status"),
        "agents_called": response.get("agents_called"),
        "review_services_called": response.get("review_services_called"),
        "logistics_origin": logistics_handoff.get("origin"),
        "logistics_destination": logistics_handoff.get("destination"),
        "logistics_route_type": logistics_handoff.get("route_type"),
        "partner_review_status": response.get("partner_review_status"),
        "placeholder_present": "PARTNER REVIEW PLACEHOLDER" in final_answer,
        "destination_missing_in_logistics_report": (
            "Destination country or final delivery location is missing" in logistics_report
        ),
        "unknown_destination_in_logistics_report": "unknown destination" in logistics_report.lower(),
        "missing_information": missing_information,
    }

    print(json.dumps(summary, indent=2, default=str))

    assert logistics_handoff.get("origin") == "India", "Logistics origin was not propagated from text."
    assert logistics_handoff.get("destination") == "USA", "Logistics destination was not propagated from text."

    assert "unknown destination" not in logistics_report.lower(), (
        "Logistics report still says unknown destination."
    )
    assert "Destination country or final delivery location is missing" not in logistics_report, (
        "Logistics report still says destination is missing."
    )

    assert "PARTNER REVIEW PLACEHOLDER" not in final_answer, (
        "Final answer still contains stale placeholder heading."
    )
    assert "PARTNER REVIEW" in final_answer, "Final answer does not contain partner review section."

    print("\nTEXT ROUTE DESTINATION CLEANUP CHECK PASSED")


if __name__ == "__main__":
    main()
