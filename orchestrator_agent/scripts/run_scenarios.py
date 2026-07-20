"""Runs demo scenarios against the four agents and verdict logic, bypassing
the LLM parser and synthesis so this works even when Gemini quota is exhausted.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator_agent.container import build_container
from orchestrator_agent.schemas.shipment_request import ParsedShipment

SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scenarios"


def run_scenario(container, scenario: dict) -> None:
    print(f"\n{'=' * 60}\n{scenario['name']}: {scenario['description']}\n{'=' * 60}")
    shipment = ParsedShipment(**scenario["input"])

    agent_errors = {}
    risk_report = compliance_report = trader_report = finance_report = {}

    try:
        risk_report = container.risk_client.call_tool_sync(
            "assess_trade_risk", {"country": shipment.country_to}
        )
    except Exception as exc:
        agent_errors["risk_agent"] = str(exc)

    try:
        compliance_report = container.compliance_client.call_tool_sync(
            "assess_compliance",
            {"product_description": shipment.product_description, "destination_country": shipment.country_to},
        )
    except Exception as exc:
        agent_errors["compliance_agent"] = str(exc)

    try:
        trader_report = container.trader_client.call_tool_sync(
            "assess_trade_plan",
            {
                "product_description": shipment.product_description,
                "country_from": shipment.country_from,
                "country_to": shipment.country_to,
                "target_market": shipment.target_market,
            },
        )
    except Exception as exc:
        agent_errors["trader_agent"] = str(exc)

    try:
        finance_shipment = {
            "shipment_id": f"SCENARIO-{scenario['name']}",
            "origin": shipment.country_from,
            "destination": shipment.country_to,
            "weight_kg": shipment.weight_kg,
            "volume_m3": shipment.volume_m3,
            "cargo_value": shipment.cargo_value,
            "currency": shipment.currency,
            "transport_mode": "sea",
            "insurance_required": True,
        }
        finance_report = container.finance_client.get_report(finance_shipment)
        trader_duty_rate = trader_report.get("handoff_payload", {}).get("duty_rate_percent")
        if trader_duty_rate is not None:
            recalculated = round(shipment.cargo_value * (trader_duty_rate / 100), 2)
            diff = recalculated - finance_report["import_duty"]
            finance_report["import_duty"] = recalculated
            finance_report["landed_cost"] = round(finance_report["landed_cost"] + diff, 2)
            finance_report["total_cost"] = round(finance_report["total_cost"] + diff, 2)
    except Exception as exc:
        agent_errors["finance_agent"] = str(exc)

    verdict = container.verdict_service.derive(
        compliance_report, trader_report, finance_report, risk_report, agent_errors
    )

    print(f"Verdict: {verdict.status}  (expected: {scenario['expected_verdict_status']})")
    print(f"Headline: {verdict.headline}")
    if verdict.blockers:
        print(f"Blockers: {verdict.blockers}")
    if verdict.warnings:
        print(f"Warnings: {verdict.warnings}")
    print(f"Agent errors: {agent_errors or 'none'}")

    match = "PASS" if verdict.status == scenario["expected_verdict_status"] else "MISMATCH"
    print(f"Result: {match}")


def main() -> None:
    container = build_container()
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        with open(path) as f:
            scenario = json.load(f)
        run_scenario(container, scenario)


if __name__ == "__main__":
    main()