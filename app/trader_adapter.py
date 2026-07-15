from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
TRADER_AGENT_DIR = ROOT_DIR / "trader_agent"

if str(TRADER_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(TRADER_AGENT_DIR))


def _safe_model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return value


def _normalize_trader_response(response: dict[str, Any]) -> dict[str, Any]:
    """Normalize Avishi's Trader Agent response into our shared backend contract."""

    if response.get("status") == "partial":
        response["status"] = "partial_plan_needs_more_information"

    response.setdefault("agent_name", "trader_agent")
    response.setdefault("summary", "")
    response.setdefault("plan", {})
    response.setdefault("report", "")
    response.setdefault("input_resolution", {})
    response.setdefault("missing_information", [])
    response.setdefault("handoff_payload", {})
    response.setdefault("handoff_requests", [])

    return response


def run_trader_agent(data: dict[str, Any], use_reasoning: bool = True) -> dict[str, Any]:
    """Run Trader Agent using the shared agent contract.

    Expected fields:
    - product_description
    - country_from
    - country_to
    - target_market
    """

    product_description = (
        data.get("product_description")
        or data.get("product_name")
        or data.get("item_name")
        or data.get("description")
    )
    country_from = data.get("country_from") or data.get("origin_country")
    country_to = data.get("country_to") or data.get("destination_country")
    target_market = data.get("target_market") or country_to

    missing = []
    if not product_description:
        missing.append("product_description")
    if not country_from:
        missing.append("country_from")
    if not country_to:
        missing.append("country_to")
    if not target_market:
        missing.append("target_market")

    if missing:
        return {
            "agent_name": "trader_agent",
            "status": "needs_more_information",
            "summary": "Trader Agent needs more information before assessing the trade plan.",
            "plan": {},
            "report": "",
            "input_resolution": {
                "product_description": product_description,
                "country_from": country_from,
                "country_to": country_to,
                "target_market": target_market,
            },
            "missing_information": missing,
            "handoff_payload": {},
            "handoff_requests": [],
        }

    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=ROOT_DIR / ".env", override=True)

        if use_reasoning:
            from trader_agent.server import assess_trade_plan_with_reasoning

            result = assess_trade_plan_with_reasoning(
                product_description=str(product_description),
                country_from=str(country_from),
                country_to=str(country_to),
                target_market=str(target_market),
            )
        else:
            from trader_agent.server import assess_trade_plan

            result = assess_trade_plan(
                product_description=str(product_description),
                country_from=str(country_from),
                country_to=str(country_to),
                target_market=str(target_market),
            )

        dumped = _safe_model_dump(result)
        if isinstance(dumped, dict):
            return _normalize_trader_response(dumped)

        return {
            "agent_name": "trader_agent",
            "status": "error",
            "summary": "Trader Agent returned an unsupported response type.",
            "plan": {},
            "report": str(dumped),
            "input_resolution": data,
            "missing_information": [],
            "handoff_payload": {},
            "handoff_requests": [],
        }

    except Exception as exc:
        return {
            "agent_name": "trader_agent",
            "status": "error",
            "summary": f"Trader Agent failed: {exc}",
            "plan": {},
            "report": "",
            "input_resolution": data,
            "missing_information": [],
            "handoff_payload": {},
            "handoff_requests": [],
        }
