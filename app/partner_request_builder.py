from __future__ import annotations

from typing import Any

from app.partner_review_payload_validator import validate_partner_review_payload


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("selected_items"), list):
        return payload["selected_items"]

    if isinstance(payload.get("items"), list):
        return payload["items"]

    return []


def _origin(payload: dict[str, Any]) -> Any:
    return payload.get("origin") or payload.get("origin_country")


def _destination(payload: dict[str, Any]) -> Any:
    return payload.get("destination") or payload.get("destination_country")


def _product_name(item: dict[str, Any]) -> Any:
    return item.get("product_name") or item.get("name")


def _product_category(item: dict[str, Any]) -> Any:
    return item.get("category") or item.get("product_category")


def _item_declared_value(item: dict[str, Any]) -> Any:
    return item.get("estimated_total_cost_usd") or item.get("declared_value_usd")


def build_partner_agent_requests(
    payload: dict[str, Any],
    request_id: str | None = None,
) -> dict[str, Any]:
    validation = validate_partner_review_payload(payload)
    resolved_request_id = request_id or payload.get("request_id")
    origin_country = _origin(payload)
    destination_country = _destination(payload)
    items = _extract_items(payload)

    if not validation["is_valid"]:
        return {
            "request_id": resolved_request_id,
            "is_ready_for_partner_calls": False,
            "payload_validation": validation,
            "risk_agent": None,
            "compliance_agent": [],
            "trader_agent": [],
            "finance_agent": None,
        }

    compliance_requests = []
    trader_requests = []

    for item in items:
        product_name = _product_name(item)
        product_category = _product_category(item)

        compliance_requests.append(
            {
                "product_name": product_name,
                "product_category": product_category,
                "origin_country": origin_country,
                "destination_country": destination_country,
                "request_id": resolved_request_id,
            }
        )

        trader_requests.append(
            {
                "product_name": product_name,
                "product_category": product_category,
                "origin_country": origin_country,
                "destination_country": destination_country,
                "declared_value_usd": _item_declared_value(item),
                "request_id": resolved_request_id,
            }
        )

    return {
        "request_id": resolved_request_id,
        "is_ready_for_partner_calls": True,
        "payload_validation": validation,
        "risk_agent": {
            "destination_country": destination_country,
            "request_id": resolved_request_id,
        },
        "compliance_agent": compliance_requests,
        "trader_agent": trader_requests,
        "finance_agent": {
            "origin_country": origin_country,
            "destination_country": destination_country,
            "total_cbm": payload.get("total_cbm"),
            "total_weight_kg": payload.get("total_weight_kg"),
            "declared_value_usd": payload.get("declared_value_usd"),
            "duty_rate_percent": payload.get("duty_rate_percent"),
            "selling_price_usd": payload.get("selling_price_usd"),
            "request_id": resolved_request_id,
        },
    }
