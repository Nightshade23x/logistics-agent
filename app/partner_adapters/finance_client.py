from __future__ import annotations

from typing import Any

from app.partner_adapters.base import build_not_configured_response


def calculate_landed_cost(
    origin_country: str,
    destination_country: str,
    total_cbm: float | None = None,
    total_weight_kg: float | None = None,
    declared_value_usd: float | None = None,
    duty_rate_percent: float | None = None,
    selling_price_usd: float | None = None,
    request_id: str | None = None,
    rest_base_url: str | None = None,
) -> dict[str, Any]:
    if not rest_base_url:
        response = build_not_configured_response(
            agent_name="finance_agent",
            required_connection="Finance REST API",
        )
        response["handoff_payload"] = {
            "origin_country": origin_country,
            "destination_country": destination_country,
            "total_cbm": total_cbm,
            "total_weight_kg": total_weight_kg,
            "declared_value_usd": declared_value_usd,
            "duty_rate_percent": duty_rate_percent,
            "selling_price_usd": selling_price_usd,
            "request_id": request_id,
        }
        return response

    return {
        "agent_name": "finance_agent",
        "status": "not_implemented",
        "summary": "Finance Agent REST call placeholder. Live REST call will be added after partner endpoint details are available.",
        "findings": {
            "origin_country": origin_country,
            "destination_country": destination_country,
            "total_cbm": total_cbm,
            "total_weight_kg": total_weight_kg,
            "declared_value_usd": declared_value_usd,
            "duty_rate_percent": duty_rate_percent,
            "selling_price_usd": selling_price_usd,
            "rest_base_url": rest_base_url,
        },
        "unverified": ["live_rest_response", "freight_cost", "insurance", "taxes", "landed_cost", "roi"],
        "handoff_payload": {
            "origin_country": origin_country,
            "destination_country": destination_country,
            "total_cbm": total_cbm,
            "total_weight_kg": total_weight_kg,
            "declared_value_usd": declared_value_usd,
            "duty_rate_percent": duty_rate_percent,
            "selling_price_usd": selling_price_usd,
            "request_id": request_id,
        },
        "error": None,
    }
