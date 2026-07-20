from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.shopping_risk import assess_supplier_option_risk, summarize_procurement_risk


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "suppliers" / "supplier_catalog.json"


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().replace("-", " ").split())


def _singularize(word: str) -> str:
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


def _tokens(text: str) -> set[str]:
    return {_singularize(token) for token in _normalize(text).split()}


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _normalize_country_list(values: Any) -> list[str]:
    if not values:
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def get_shopping_preferences(request_data: dict[str, Any]) -> dict[str, Any]:
    preferences = request_data.get("preferences") or {}

    return {
        "preferred_supplier_countries": _normalize_country_list(
            preferences.get("preferred_supplier_countries")
        ),
        "excluded_supplier_countries": _normalize_country_list(
            preferences.get("excluded_supplier_countries")
        ),
        "max_lead_time_days": _optional_int(preferences.get("max_lead_time_days")),
        "minimum_quality_score": _optional_float(preferences.get("minimum_quality_score")),
        "max_budget_usd": _optional_float(preferences.get("max_budget_usd")),
    }


def load_supplier_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    catalog_path = path or CATALOG_PATH
    with catalog_path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _match_score(requested_name: str, product_name: str) -> float:
    requested = _normalize(requested_name)
    product = _normalize(product_name)

    if requested == product:
        return 1.0

    requested_tokens = _tokens(requested)
    product_tokens = _tokens(product)

    if requested_tokens == product_tokens:
        return 0.98

    if requested in product or product in requested:
        return 0.9

    token_overlap = 0.0
    if requested_tokens and product_tokens:
        token_overlap = len(requested_tokens.intersection(product_tokens)) / len(
            requested_tokens.union(product_tokens)
        )

    sequence_score = SequenceMatcher(None, requested, product).ratio()
    return max(token_overlap, sequence_score)


def find_supplier_matches(
    item_name: str,
    catalog: list[dict[str, Any]],
    threshold: float = 0.72,
) -> list[dict[str, Any]]:
    matches = []

    for supplier_item in catalog:
        score = _match_score(item_name, supplier_item["product_name"])
        if score >= threshold:
            match = dict(supplier_item)
            match["match_score"] = round(score, 2)
            matches.append(match)

    return sorted(
        matches,
        key=lambda item: (
            -item["match_score"],
            item["unit_price_usd"],
            -item["supplier_rating"],
        ),
    )


def find_alternatives(
    item_name: str,
    catalog: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    alternatives = []

    for supplier_item in catalog:
        score = _match_score(item_name, supplier_item["product_name"])
        option = dict(supplier_item)
        option["similarity_score"] = round(score, 2)
        alternatives.append(option)

    return sorted(alternatives, key=lambda item: -item["similarity_score"])[:limit]


def _availability_status(quantity: int, supplier_item: dict[str, Any]) -> str:
    if quantity < int(supplier_item["minimum_order_quantity"]):
        return "below_minimum_order_quantity"
    if quantity > int(supplier_item["available_quantity"]):
        return "insufficient_stock"
    return "available"


def _country_key(country: str) -> str:
    return country.strip().lower()


def _is_preferred_country(
    supplier_item: dict[str, Any],
    preferences: dict[str, Any],
) -> bool:
    preferred_countries = {
        _country_key(country)
        for country in preferences.get("preferred_supplier_countries", [])
    }

    if not preferred_countries:
        return False

    return _country_key(supplier_item["country"]) in preferred_countries


def _preference_issues(
    supplier_item: dict[str, Any],
    preferences: dict[str, Any],
) -> list[str]:
    issues = []

    supplier_country = _country_key(supplier_item["country"])
    excluded_countries = {
        _country_key(country)
        for country in preferences.get("excluded_supplier_countries", [])
    }

    if supplier_country in excluded_countries:
        issues.append("excluded_supplier_country")

    max_lead_time_days = preferences.get("max_lead_time_days")
    if max_lead_time_days is not None and int(supplier_item["lead_time_days"]) > max_lead_time_days:
        issues.append("lead_time_above_limit")

    minimum_quality_score = preferences.get("minimum_quality_score")
    if minimum_quality_score is not None and float(supplier_item["quality_score"]) < minimum_quality_score:
        issues.append("quality_below_minimum")

    return issues


def _score_supplier(
    quantity: int,
    supplier_item: dict[str, Any],
    preferences: dict[str, Any],
) -> float:
    if _availability_status(quantity, supplier_item) != "available":
        return 0.0

    if _preference_issues(supplier_item, preferences):
        return 0.0

    price = float(supplier_item["unit_price_usd"])
    quality = float(supplier_item["quality_score"])
    rating = float(supplier_item["supplier_rating"])
    lead_time = float(supplier_item["lead_time_days"])

    price_score = max(0.0, 10 - min(price / 50, 10))
    quality_score = quality
    rating_score = rating * 2
    lead_time_score = max(0.0, 10 - min(lead_time / 5, 10))
    preferred_country_bonus = 0.5 if _is_preferred_country(supplier_item, preferences) else 0.0

    score = (
        (price_score * 0.3)
        + (quality_score * 0.3)
        + (rating_score * 0.25)
        + (lead_time_score * 0.15)
        + preferred_country_bonus
    )

    return round(min(score, 10.0), 2)


def _build_supplier_option(
    quantity: int,
    supplier_item: dict[str, Any],
    preferences: dict[str, Any],
) -> dict[str, Any]:
    total_cost = quantity * float(supplier_item["unit_price_usd"])
    availability = _availability_status(quantity, supplier_item)
    preference_issues = _preference_issues(supplier_item, preferences)
    is_eligible = availability == "available" and not preference_issues

    option = {
        "supplier_id": supplier_item["supplier_id"],
        "supplier_name": supplier_item["supplier_name"],
        "country": supplier_item["country"],
        "product_name": supplier_item["product_name"],
        "category": supplier_item["category"],
        "unit_price_usd": supplier_item["unit_price_usd"],
        "requested_quantity": quantity,
        "estimated_total_cost_usd": round(total_cost, 2),
        "quality_score": supplier_item["quality_score"],
        "supplier_rating": supplier_item["supplier_rating"],
        "lead_time_days": supplier_item["lead_time_days"],
        "minimum_order_quantity": supplier_item["minimum_order_quantity"],
        "available_quantity": supplier_item["available_quantity"],
        "availability_status": availability,
        "preference_issues": preference_issues,
        "selection_status": "eligible" if is_eligible else "not_eligible",
        "is_preferred_country": _is_preferred_country(supplier_item, preferences),
        "match_score": supplier_item.get("match_score", 0),
        "overall_score": _score_supplier(quantity, supplier_item, preferences),
        "notes": supplier_item.get("notes", ""),
    }

    option.update(assess_supplier_option_risk(option))

    return option


def _select_recommendations(options: list[dict[str, Any]]) -> dict[str, Any]:
    eligible_options = [
        option
        for option in options
        if option["selection_status"] == "eligible"
    ]

    if not eligible_options:
        return {"cheapest": None, "best_quality": None, "balanced": None}

    cheapest = min(eligible_options, key=lambda option: option["unit_price_usd"])

    best_quality = max(
        eligible_options,
        key=lambda option: (
            option["quality_score"],
            option["supplier_rating"],
            -option["unit_price_usd"],
        ),
    )

    balanced = max(
        eligible_options,
        key=lambda option: (
            option["overall_score"],
            option["supplier_rating"],
            -option["lead_time_days"],
        ),
    )

    return {
        "cheapest": cheapest,
        "best_quality": best_quality,
        "balanced": balanced,
    }


def evaluate_shopping_item(
    requested_item: dict[str, Any],
    catalog: list[dict[str, Any]],
    preferences: dict[str, Any],
) -> dict[str, Any]:
    item_name = requested_item["name"]
    quantity = int(requested_item["quantity"])

    matches = find_supplier_matches(item_name, catalog)
    options = [
        _build_supplier_option(quantity, match, preferences)
        for match in matches
    ]

    recommendations = _select_recommendations(options)

    issues = []
    alternatives = []

    if not matches:
        issues.append(f"{item_name}: no supplier match found.")
        alternatives = find_alternatives(item_name, catalog)

    elif not any(option["availability_status"] == "available" for option in options):
        issues.append(
            f"{item_name}: suppliers found, but none can satisfy quantity/MOQ/stock requirements."
        )
        alternatives = find_alternatives(item_name, catalog)

    elif not any(option["selection_status"] == "eligible" for option in options):
        issues.append(
            f"{item_name}: suppliers found, but all were filtered out by country, lead time, or quality preferences."
        )
        alternatives = find_alternatives(item_name, catalog)

    return {
        "requested_item": item_name,
        "requested_quantity": quantity,
        "supplier_options": options,
        "recommendations": recommendations,
        "alternatives": alternatives,
        "issues": issues,
    }


def build_shopping_plan(request_data: dict[str, Any]) -> dict[str, Any]:
    catalog = load_supplier_catalog()
    requested_items = request_data.get("items", [])
    preferences = get_shopping_preferences(request_data)

    item_results = [
        evaluate_shopping_item(item, catalog, preferences)
        for item in requested_items
    ]

    selected_items = []
    total_procurement_cost = 0.0

    for result in item_results:
        balanced = result["recommendations"].get("balanced")
        if balanced:
            selected_items.append(balanced)
            total_procurement_cost += balanced["estimated_total_cost_usd"]

    item_issues = [
        issue
        for result in item_results
        for issue in result["issues"]
    ]

    budget_issues = []
    max_budget_usd = preferences.get("max_budget_usd")
    within_budget = None

    if max_budget_usd is not None:
        within_budget = total_procurement_cost <= max_budget_usd

        if not within_budget:
            budget_issues.append(
                f"Estimated procurement cost {round(total_procurement_cost, 2)} USD exceeds max budget {max_budget_usd} USD."
            )

    all_issues = item_issues + budget_issues

    if not requested_items:
        status = "needs_more_information"
        all_issues.append("No requested items were provided.")
    elif not selected_items:
        status = "needs_more_information"
    elif item_issues:
        status = "partial_plan_needs_more_information"
    elif budget_issues:
        status = "review_required"
    else:
        status = "ready_for_review"

    procurement_risk = summarize_procurement_risk(selected_items)

    return {
        "request_context": {
            "request_id": request_data.get("request_id"),
            "customer": request_data.get("customer"),
            "destination_country": request_data.get("destination_country"),
            "preferred_currency": request_data.get("preferred_currency", "USD"),
        },
        "preferences": preferences,
        "item_results": item_results,
        "selected_items": selected_items,
        "procurement_summary": {
            "selected_supplier_count": len(selected_items),
            "estimated_total_procurement_cost_usd": round(total_procurement_cost, 2),
            "currency": "USD",
        },
        "budget_check": {
            "max_budget_usd": max_budget_usd,
            "estimated_total_procurement_cost_usd": round(total_procurement_cost, 2),
            "within_budget": within_budget,
        },
        "procurement_risk": procurement_risk,
        "issues": all_issues,
        "catalog_size": len(catalog),
        "status": status,
    }
