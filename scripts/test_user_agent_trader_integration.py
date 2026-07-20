from __future__ import annotations

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)
os.environ["USE_TRAINED_ROUTER"] = "1"

from app.user_agent import run_user_agent_from_text
from app.trader_adapter import run_trader_agent


def first(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return value


def get_nested_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def pick_product(shopping_response: dict[str, Any], prompt: str) -> str:
    payload = get_nested_dict(shopping_response.get("handoff_payload"))
    selected_items = payload.get("selected_items") or payload.get("items") or []

    if selected_items and isinstance(selected_items[0], dict):
        item = selected_items[0]
        return (
            item.get("product_name")
            or item.get("name")
            or item.get("item_name")
            or "ceramic tiles"
        )

    return (
        payload.get("product_description")
        or payload.get("product_name")
        or "ceramic tiles"
    )


def pick_origin(shopping_response: dict[str, Any], logistics_response: dict[str, Any]) -> str:
    shopping_payload = get_nested_dict(shopping_response.get("handoff_payload"))
    logistics_payload = get_nested_dict(logistics_response.get("handoff_payload"))

    return (
        first(shopping_payload.get("supplier_countries"))
        or shopping_payload.get("origin_country")
        or logistics_payload.get("origin_country")
        or "India"
    )


def pick_destination(shopping_response: dict[str, Any], logistics_response: dict[str, Any]) -> str:
    shopping_payload = get_nested_dict(shopping_response.get("handoff_payload"))
    logistics_payload = get_nested_dict(logistics_response.get("handoff_payload"))

    return (
        shopping_payload.get("destination_country")
        or logistics_payload.get("destination_country")
        or "USA"
    )


prompt = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "estimate freight and find supplier for 100 ceramic tiles from India to USA"
)

user_agent_response = run_user_agent_from_text(prompt)
specialists = get_nested_dict(user_agent_response.get("specialist_responses"))

shopping_response = get_nested_dict(specialists.get("shopping_agent"))
logistics_response = get_nested_dict(specialists.get("logistics_agent"))

trader_input = {
    "product_description": pick_product(shopping_response, prompt),
    "country_from": pick_origin(shopping_response, logistics_response),
    "country_to": pick_destination(shopping_response, logistics_response),
}
trader_input["target_market"] = trader_input["country_to"]

trader_response = run_trader_agent(trader_input, use_reasoning=True)

report = trader_response.get("report", {})
has_llm_judgment = isinstance(report, dict) and bool(report.get("llm_judgment"))

combined = {
    "prompt": prompt,
    "user_agent": {
        "status": user_agent_response.get("status"),
        "router_source": user_agent_response.get("router_source"),
        "agents_called": user_agent_response.get("agents_called"),
    },
    "trader_input": trader_input,
    "trader_agent": {
        "status": trader_response.get("status"),
        "summary": trader_response.get("summary"),
        "missing_information": trader_response.get("missing_information"),
        "handoff_payload": trader_response.get("handoff_payload"),
        "has_llm_judgment": has_llm_judgment,
    },
}

print(json.dumps(combined, indent=2, default=str))
