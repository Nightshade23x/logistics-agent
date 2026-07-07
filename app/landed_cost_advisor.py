from __future__ import annotations

from typing import Any


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _clean_text(value: Any) -> str:
    text = str(value)

    replacements = {
        "wereestimated": "were estimated",
        "propertieswere": "properties were",
        "abovenon-stackable": "above non-stackable",
        "cushioning,strong": "cushioning, strong",
        "forthis": "for this",
        "IncotermFOB": "Incoterm FOB",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _get_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _get_specialist_response(
    user_agent_response: dict[str, Any],
    agent_name: str,
) -> dict[str, Any]:
    specialist_responses = _get_dict(user_agent_response.get("specialist_responses"))
    return _get_dict(specialist_responses.get(agent_name))


def _get_handoff_payload(agent_response: dict[str, Any]) -> dict[str, Any]:
    return _get_dict(agent_response.get("handoff_payload"))


def _first_positive_number(values: list[Any]) -> float | None:
    for value in values:
        number = _as_float(value)

        if number is not None and number > 0:
            return number

    return None


def _extract_procurement_value(user_agent_response: dict[str, Any]) -> float | None:
    shopping_response = _get_specialist_response(user_agent_response, "shopping_agent")
    shopping_handoff = _get_handoff_payload(shopping_response)
    partner_review = _get_dict(user_agent_response.get("partner_review"))

    return _first_positive_number(
        [
            shopping_handoff.get("estimated_total_procurement_cost_usd"),
            shopping_handoff.get("declared_value_usd"),
            shopping_response.get("estimated_total_procurement_cost_usd"),
            partner_review.get("declared_value_usd"),
            user_agent_response.get("declared_value_usd"),
            user_agent_response.get("commercial_value_usd"),
        ]
    )


def _extract_logistics_values(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    logistics_response = _get_specialist_response(user_agent_response, "logistics_agent")
    logistics_handoff = _get_handoff_payload(logistics_response)

    logistics_quality_review = _get_dict(user_agent_response.get("logistics_quality_review"))
    freight_mode_advice = _get_dict(logistics_quality_review.get("freight_mode_advice"))

    return {
        "total_cbm": _as_float(logistics_handoff.get("total_cbm")),
        "total_weight_kg": _as_float(logistics_handoff.get("total_weight_kg")),
        "recommended_container": logistics_handoff.get("recommended_container"),
        "recommended_load_type": logistics_handoff.get("recommended_load_type"),
        "primary_freight_mode": freight_mode_advice.get("primary_mode"),
    }


def _extract_trade_values(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    trade_terms_advice = _get_dict(user_agent_response.get("trade_terms_advice"))

    return {
        "incoterm": trade_terms_advice.get("incoterm") or user_agent_response.get("incoterm"),
        "origin_country": trade_terms_advice.get("origin_country") or user_agent_response.get("origin_country"),
        "destination_country": trade_terms_advice.get("destination_country") or user_agent_response.get("destination_country"),
    }


def _extract_cost_inputs(user_agent_response: dict[str, Any]) -> dict[str, float | None]:
    finance_payload = _get_dict(user_agent_response.get("finance_payload"))
    partner_review = _get_dict(user_agent_response.get("partner_review"))

    return {
        "freight_quote_usd": _first_positive_number(
            [
                user_agent_response.get("freight_quote_usd"),
                user_agent_response.get("freight_cost_usd"),
                finance_payload.get("freight_quote_usd"),
                finance_payload.get("freight_cost_usd"),
                partner_review.get("freight_quote_usd"),
            ]
        ),
        "insurance_premium_usd": _first_positive_number(
            [
                user_agent_response.get("insurance_premium_usd"),
                user_agent_response.get("insurance_cost_usd"),
                finance_payload.get("insurance_premium_usd"),
                finance_payload.get("insurance_cost_usd"),
                partner_review.get("insurance_premium_usd"),
            ]
        ),
        "duty_rate_percent": _first_positive_number(
            [
                user_agent_response.get("duty_rate_percent"),
                finance_payload.get("duty_rate_percent"),
                partner_review.get("duty_rate_percent"),
            ]
        ),
        "import_tax_rate_percent": _first_positive_number(
            [
                user_agent_response.get("import_tax_rate_percent"),
                user_agent_response.get("vat_rate_percent"),
                finance_payload.get("import_tax_rate_percent"),
                finance_payload.get("vat_rate_percent"),
                partner_review.get("import_tax_rate_percent"),
            ]
        ),
        "customs_brokerage_usd": _first_positive_number(
            [
                user_agent_response.get("customs_brokerage_usd"),
                finance_payload.get("customs_brokerage_usd"),
                partner_review.get("customs_brokerage_usd"),
            ]
        ),
        "local_delivery_usd": _first_positive_number(
            [
                user_agent_response.get("local_delivery_usd"),
                finance_payload.get("local_delivery_usd"),
                partner_review.get("local_delivery_usd"),
            ]
        ),
    }


def build_landed_cost_advice(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    procurement_value_usd = _extract_procurement_value(user_agent_response)
    logistics_values = _extract_logistics_values(user_agent_response)
    trade_values = _extract_trade_values(user_agent_response)
    cost_inputs = _extract_cost_inputs(user_agent_response)

    missing_cost_inputs: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    blockers: list[str] = []
    known_inputs: dict[str, Any] = {}

    if procurement_value_usd is None:
        missing_cost_inputs.append("procurement_value_usd")
        blockers.append("Procurement value or declared value is missing.")
    else:
        known_inputs["procurement_value_usd"] = procurement_value_usd

    for key, value in logistics_values.items():
        if value is not None:
            known_inputs[key] = value

    for key, value in trade_values.items():
        if value:
            known_inputs[key] = value

    for key, value in cost_inputs.items():
        if value is None:
            missing_cost_inputs.append(key)
        else:
            known_inputs[key] = value

    if not trade_values.get("incoterm"):
        warnings.append("Incoterm is missing, so responsibility for freight, insurance, duties, and delivery is unclear.")

    if not trade_values.get("origin_country"):
        warnings.append("Origin country is missing, so duty and trade-program checks cannot be finalized.")

    if not trade_values.get("destination_country"):
        warnings.append("Destination country is missing, so import duty and tax checks cannot be finalized.")

    if cost_inputs["freight_quote_usd"] is None:
        recommendations.append("Get a freight quote for the selected freight mode before calculating landed cost.")

    if cost_inputs["insurance_premium_usd"] is None:
        recommendations.append("Confirm cargo insurance premium or insurance responsibility before final landed cost.")

    if cost_inputs["duty_rate_percent"] is None:
        recommendations.append("Get duty rate from the Trader Agent or customs/tariff source.")

    if cost_inputs["import_tax_rate_percent"] is None:
        recommendations.append("Confirm import tax or VAT rate for the destination country.")

    if cost_inputs["customs_brokerage_usd"] is None:
        recommendations.append("Add customs brokerage or clearance fee estimate.")

    if cost_inputs["local_delivery_usd"] is None:
        recommendations.append("Add destination local delivery or last-mile delivery estimate.")

    estimated_subtotal_known_usd = procurement_value_usd

    if estimated_subtotal_known_usd is not None:
        for key in [
            "freight_quote_usd",
            "insurance_premium_usd",
            "customs_brokerage_usd",
            "local_delivery_usd",
        ]:
            value = cost_inputs[key]

            if value is not None:
                estimated_subtotal_known_usd += value

    formula = [
        "procurement_value_usd",
        "freight_quote_usd",
        "insurance_premium_usd",
        "customs_brokerage_usd",
        "local_delivery_usd",
        "estimated_duty",
        "estimated_import_tax_or_vat",
    ]

    if blockers:
        status = "blocked"
        summary = "Landed cost advice is blocked because essential value information is missing."
    elif missing_cost_inputs:
        status = "needs_more_information"
        summary = "Landed cost advice needs more cost inputs before a reliable estimate can be produced."
    elif warnings:
        status = "review_required"
        summary = "Landed cost advice is usable but trade assumptions should be reviewed."
    else:
        status = "clear"
        summary = "Landed cost advice has enough first-pass inputs."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "known_inputs": known_inputs,
        "missing_cost_inputs": list(dict.fromkeys(missing_cost_inputs)),
        "estimated_subtotal_known_usd": estimated_subtotal_known_usd,
        "landed_cost_formula": formula,
        "blockers": list(dict.fromkeys(_clean_text(item) for item in blockers)),
        "warnings": list(dict.fromkeys(_clean_text(item) for item in warnings)),
        "recommendations": list(dict.fromkeys(_clean_text(item) for item in recommendations)),
    }
