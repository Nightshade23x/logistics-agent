from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

os.environ["USE_TRAINED_ROUTER"] = "1"
os.environ["ENABLE_TRADER_AGENT"] = "1"
os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json,
    run_user_agent_from_text,
)


def _find_document_pair() -> list[str]:
    candidates = list(Path("data").rglob("*"))

    invoice = None
    packing = None

    for path in candidates:
        if not path.is_file():
            continue

        name = path.name.lower()

        if invoice is None and "invoice" in name:
            invoice = path

        if packing is None and ("packing" in name or "pack" in name):
            packing = path

    if invoice is None or packing is None:
        raise AssertionError(
            "Could not find sample invoice and packing-list documents under data/."
        )

    return [str(invoice), str(packing)]


def _partner_payload(response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("partner_review_payload")
    assert isinstance(payload, dict), "partner_review_payload missing or not a dict"
    return payload


def _partner_review(response: dict[str, Any]) -> dict[str, Any]:
    review = response.get("partner_review")
    if isinstance(review, dict):
        return review

    specialist = response.get("specialist_responses", {})
    if isinstance(specialist, dict) and isinstance(specialist.get("partner_review_service"), dict):
        return specialist["partner_review_service"]

    raise AssertionError("partner_review missing")


def _assert_common_contract(
    flow_name: str,
    response: dict[str, Any],
    *,
    expected_origin: str | None = None,
    expected_destination: str | None = None,
    require_cost_fields: bool = False,
) -> dict[str, Any]:
    payload = _partner_payload(response)
    review = _partner_review(response)

    assert "partner_review_service" in (response.get("review_services_called") or []), flow_name
    assert response.get("partner_review_attempted") is True, flow_name
    assert response.get("partner_review_service_called") is True, flow_name
    assert response.get("partner_review_mode") == "local_fallback", flow_name
    assert response.get("live_orchestrator_configured") is False, flow_name

    assert payload.get("origin") or payload.get("origin_country"), f"{flow_name}: missing origin"
    assert payload.get("destination") or payload.get("destination_country"), f"{flow_name}: missing destination"

    if expected_origin:
        assert payload.get("origin") == expected_origin, f"{flow_name}: wrong origin"
        assert payload.get("origin_country") == expected_origin, f"{flow_name}: wrong origin_country"

    if expected_destination:
        assert payload.get("destination") == expected_destination, f"{flow_name}: wrong destination"
        assert payload.get("destination_country") == expected_destination, f"{flow_name}: wrong destination_country"

    missing_required = review.get("missing_required_fields") or []
    assert not any("destination" in str(item).lower() for item in missing_required), (
        f"{flow_name}: destination should not be missing"
    )

    if require_cost_fields:
        assert payload.get("incoterm") == "CIF", f"{flow_name}: missing incoterm"
        assert payload.get("freight_quote_usd") == 1200.0, f"{flow_name}: missing freight_quote_usd"
        assert payload.get("insurance_premium_usd") == 250.0, f"{flow_name}: missing insurance_premium_usd"
        assert payload.get("duty_rate_percent") == 5.0, f"{flow_name}: missing duty_rate_percent"
        assert payload.get("import_tax_rate_percent") == 8.0, f"{flow_name}: missing import_tax_rate_percent"

    return {
        "flow": flow_name,
        "status": response.get("status"),
        "agents_called": response.get("agents_called"),
        "review_services_called": response.get("review_services_called"),
        "partner_review_status": response.get("partner_review_status"),
        "partner_review_mode": response.get("partner_review_mode"),
        "partner_payload": {
            "origin": payload.get("origin"),
            "origin_country": payload.get("origin_country"),
            "destination": payload.get("destination"),
            "destination_country": payload.get("destination_country"),
            "incoterm": payload.get("incoterm"),
            "freight_quote_usd": payload.get("freight_quote_usd"),
            "insurance_premium_usd": payload.get("insurance_premium_usd"),
            "duty_rate_percent": payload.get("duty_rate_percent"),
            "import_tax_rate_percent": payload.get("import_tax_rate_percent"),
            "total_cbm": payload.get("total_cbm"),
            "total_weight_kg": payload.get("total_weight_kg"),
        },
        "missing_required_fields": missing_required,
    }


def main() -> None:
    results = []

    text_prompt = (
        "estimate freight and find supplier for 100 ceramic tiles from India to USA. "
        "Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. "
        "Duty rate is 5 percent. Import tax rate is 8 percent."
    )

    text_response = run_user_agent_from_text(text_prompt)
    results.append(
        _assert_common_contract(
            "text_shopping_logistics_partner",
            text_response,
            expected_origin="India",
            expected_destination="USA",
            require_cost_fields=True,
        )
    )

    document_paths = _find_document_pair()
    document_response = run_user_agent_from_files(document_paths)
    results.append(
        _assert_common_contract(
            "document_logistics_partner",
            document_response,
            expected_origin="India",
            expected_destination="USA",
            require_cost_fields=False,
        )
    )

    json_request = {
        "origin": "India",
        "destination": "USA",
        "incoterm": "CIF",
        "freight_quote_usd": 1200.0,
        "insurance_premium_usd": 250.0,
        "duty_rate_percent": 5.0,
        "import_tax_rate_percent": 8.0,
        "items": [
            {
                "name": "Ceramic tiles",
                "quantity": 100,
                "length": 60,
                "width": 60,
                "height": 8,
                "dimension_unit": "cm",
                "weight": 12,
                "weight_unit": "kg",
                "declared_value_usd": 18500,
            }
        ],
    }

    json_response = run_user_agent_from_json(json_request)
    results.append(
        _assert_common_contract(
            "json_logistics_partner",
            json_response,
            expected_origin="India",
            expected_destination="USA",
            require_cost_fields=True,
        )
    )

    print(json.dumps(results, indent=2, default=str))
    print("\nPARTNER PAYLOAD CONTRACT CHECK PASSED")


if __name__ == "__main__":
    main()
