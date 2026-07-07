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
        "likelytoo": "likely too",
        "aquote": "a quote",
        "neededfor": "needed for",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _get_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _get_shopping_response(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    specialist_responses = _get_dict(user_agent_response.get("specialist_responses"))
    return _get_dict(specialist_responses.get("shopping_agent"))


def _get_handoff_payload(shopping_response: dict[str, Any]) -> dict[str, Any]:
    return _get_dict(shopping_response.get("handoff_payload"))


def _extract_items_from_container(container: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for key in [
        "selected_items",
        "items",
        "products",
        "supplier_items",
        "recommended_items",
    ]:
        for item in _as_list(container.get(key)):
            if isinstance(item, dict):
                items.append(item)

    return items


def _extract_supplier_options(shopping_response: dict[str, Any]) -> list[dict[str, Any]]:
    handoff_payload = _get_handoff_payload(shopping_response)

    supplier_options: list[dict[str, Any]] = []

    for container in [shopping_response, handoff_payload]:
        for key in [
            "shortlisted_suppliers",
            "supplier_shortlist",
            "shortlist",
            "supplier_options",
            "ranked_suppliers",
            "recommended_suppliers",
        ]:
            for option in _as_list(container.get(key)):
                if isinstance(option, dict):
                    supplier_options.append(option)

        supplier_options.extend(_extract_items_from_container(container))

    unique_options: list[dict[str, Any]] = []
    seen: set[str] = set()

    for option in supplier_options:
        identity = repr(sorted(option.items()))

        if identity in seen:
            continue

        unique_options.append(option)
        seen.add(identity)

    return unique_options


def _extract_selected_items(shopping_response: dict[str, Any]) -> list[dict[str, Any]]:
    handoff_payload = _get_handoff_payload(shopping_response)
    selected_items = _extract_items_from_container(handoff_payload)

    if not selected_items:
        selected_items = _extract_items_from_container(shopping_response)

    unique_items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in selected_items:
        identity = repr(sorted(item.items()))

        if identity in seen:
            continue

        unique_items.append(item)
        seen.add(identity)

    return unique_items


def _extract_preferences(shopping_response: dict[str, Any]) -> dict[str, Any]:
    handoff_payload = _get_handoff_payload(shopping_response)

    preferences = handoff_payload.get("preferences") or shopping_response.get("preferences")

    if isinstance(preferences, dict):
        return preferences

    return {}


def _item_name(item: dict[str, Any]) -> str:
    return _clean_text(
        item.get("product_name")
        or item.get("name")
        or item.get("item_name")
        or "Unnamed item"
    )


def build_procurement_advice(user_agent_response: dict[str, Any]) -> dict[str, Any]:
    shopping_response = _get_shopping_response(user_agent_response)

    if not shopping_response:
        return {
            "applicable": False,
            "status": "not_applicable",
            "summary": "No Shopping Agent response was found for this request.",
            "selected_items_count": 0,
            "supplier_options_count": 0,
            "warnings": [],
            "recommendations": [],
            "negotiation_points": [],
            "user_questions": [],
        }

    selected_items = _extract_selected_items(shopping_response)
    supplier_options = _extract_supplier_options(shopping_response)
    preferences = _extract_preferences(shopping_response)

    selected_countries = set()
    selected_suppliers = set()
    product_names = set()

    warnings: list[str] = []
    recommendations: list[str] = []
    negotiation_points: list[str] = []
    user_questions: list[str] = []

    estimated_total = _as_float(
        _get_handoff_payload(shopping_response).get("estimated_total_procurement_cost_usd")
        or shopping_response.get("estimated_total_procurement_cost_usd")
    )

    budget = _as_float(
        preferences.get("budget_usd")
        or preferences.get("max_budget_usd")
        or _get_handoff_payload(shopping_response).get("budget_usd")
    )

    if not selected_items:
        warnings.append("No selected supplier items were found.")
        user_questions.append("Which products and quantities should be sourced?")
    else:
        for item in selected_items:
            product_names.add(_item_name(item))

            supplier_name = item.get("supplier_name") or item.get("supplier") or item.get("vendor")
            country = item.get("country") or item.get("supplier_country") or item.get("origin_country")

            if supplier_name:
                selected_suppliers.add(_clean_text(supplier_name))

            if country:
                selected_countries.add(_clean_text(country).lower())

            lead_time = _as_float(item.get("lead_time_days"))
            if lead_time is None:
                warnings.append(f"{_item_name(item)}: lead time is not confirmed.")

            moq = _as_float(item.get("minimum_order_quantity") or item.get("moq"))
            quantity = _as_float(item.get("requested_quantity") or item.get("quantity"))

            if moq is not None and quantity is not None and quantity < moq:
                warnings.append(f"{_item_name(item)}: requested quantity is below supplier MOQ.")

            unit_price = _as_float(item.get("unit_price_usd") or item.get("price_usd"))
            if unit_price is None:
                warnings.append(f"{_item_name(item)}: unit price is not confirmed.")

    if len(selected_suppliers) == 1 and len(selected_items) > 1:
        warnings.append("Multiple items depend on a single selected supplier.")
        recommendations.append("Keep at least one backup supplier for critical products.")

    if len(selected_countries) == 1 and selected_countries:
        recommendations.append("Check whether single-country sourcing risk is acceptable.")

    if supplier_options and len(supplier_options) > len(selected_items):
        recommendations.append("Keep shortlisted suppliers as backups before issuing final purchase orders.")
    elif selected_items:
        warnings.append("No clear backup supplier options were found.")
        recommendations.append("Ask Shopping Agent for backup suppliers before final procurement approval.")

    if estimated_total is not None:
        negotiation_points.append(f"Use estimated total procurement cost {estimated_total} USD as the negotiation baseline.")

    if budget is not None and estimated_total is not None:
        if estimated_total > budget:
            warnings.append(f"Estimated procurement cost {estimated_total} USD exceeds budget {budget} USD.")
            negotiation_points.append("Negotiate price reduction, reduce quantity, or request alternative suppliers.")
        else:
            negotiation_points.append("Confirm whether supplier can hold quoted price within the user's budget.")

    negotiation_points.append("Confirm payment terms, production lead time, warranty, and return/replacement policy.")
    negotiation_points.append("Confirm packaging standard, export carton strength, and labeling requirements.")
    negotiation_points.append("Request proforma invoice before final purchase order approval.")

    if not preferences:
        user_questions.append("Are there preferred countries, excluded countries, budget limits, or lead-time limits?")

    if warnings:
        status = "review_required"
        summary = "Procurement advice is usable but supplier selection should be reviewed."
    else:
        status = "clear"
        summary = "Procurement advice is clear for first-pass supplier planning."

    return {
        "applicable": True,
        "status": status,
        "summary": summary,
        "selected_items_count": len(selected_items),
        "supplier_options_count": len(supplier_options),
        "selected_product_names": sorted(product_names),
        "selected_supplier_countries": sorted(selected_countries),
        "estimated_total_procurement_cost_usd": estimated_total,
        "budget_usd": budget,
        "warnings": list(dict.fromkeys(_clean_text(item) for item in warnings)),
        "recommendations": list(dict.fromkeys(_clean_text(item) for item in recommendations)),
        "negotiation_points": list(dict.fromkeys(_clean_text(item) for item in negotiation_points)),
        "user_questions": list(dict.fromkeys(_clean_text(item) for item in user_questions)),
    }
