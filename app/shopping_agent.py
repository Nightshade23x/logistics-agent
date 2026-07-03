from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


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


def load_supplier_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    catalog_path = path or CATALOG_PATH

    with catalog_path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _match_score(requested_name: str, supplier_product_name: str) -> float:
    requested = _normalize(requested_name)
    product = _normalize(supplier_product_name)

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
    matches: list[dict[str, Any]] = []

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
    scored_items = []

    for supplier_item in catalog:
        score = _match_score(item_name, supplier_item["product_name"])
        alternative = dict(supplier_item)
        alternative["similarity_score"] = round(score, 2)
        scored_items.append(alternative)

    return sorted(
        scored_items,
        key=lambda item: -item["similarity_score"],
    )[:limit]


def _availability_status(requested_quantity: int, supplier_item: dict[str, Any]) -> str:
    minimum_order = int(supplier_item["minimum_order_quantity"])
    available_quantity = int(supplier_item["available_quantity"])

    if requested_quantity < minimum_order:
        return "below_minimum_order_quantity"

    if requested_quantity > available_quantity:
        return "insufficient_stock"

    return "available"


def _score_supplier(requested_quantity: int, supplier_item: dict[str, Any]) -> float:
    availability = _availability_status(requested_quantity, supplier_item)

    if availability != "available":
        return 0.0

    price = float(supplier_item["unit_price_usd"])
    quality = float(supplier_item["quality_score"])
    rating = float(supplier_item["supplier_rating"])
    lead_time = float(supplier_item["lead_time_days"])

    price_score = max(0.0, 10 - min(price / 50, 10))
    quality_score = quality
    rating_score = rating * 2
    lead_time_score = max(0.0, 10 - min(lead_time / 5, 10))

    return round(
        (price_score * 0.3)
        + (quality_score * 0.3)
        + (rating_score * 0.25)
        + (lead_time_score * 0.15),
        2,
    )


def _build_supplier_option(
    requested_quantity: int,
    supplier_item: dict[str, Any],
) -> dict[str, Any]:
    total_cost = requested_quantity * float(supplier_item["unit_price_usd"])
    availability = _availability_status(requested_quantity, supplier_item)

    return {
        "supplier_id": supplier_item["supplier_id"],
        "supplier_name": supplier_item["supplier_name"],
        "country": supplier_item["country"],
        "product_name": supplier_item["product_name"],
        "category": supplier_item["category"],
        "unit_price_usd": supplier_item["unit_price_usd"],
        "requested_quantity": requested_quantity,
        "estimated_total_cost_usd": round(total_cost, 2),
        "quality_score": supplier_item["quality_score"],
        "supplier_rating": supplier_item["supplier_rating"],
        "lead_time_days": supplier_item["lead_time_days"],
        "minimum_order_quantity": supplier_item["minimum_order_quantity"],
        "available_quantity": supplier_item["available_quantity"],
        "availability_status": availability,
        "match_score": supplier_item.get("match_score", 0),
        "overall_score": _score_supplier(requested_quantity, supplier_item),
        "notes": supplier_item.get("notes", ""),
    }


def _select_recommendations(options: list[dict[str, Any]]) -> dict[str, Any]:
    available_options = [
        option
        for option in options
        if option["availability_status"] == "available"
    ]

    if not available_options:
        return {
            "cheapest": None,
            "best_quality": None,
            "balanced": None,
        }

    cheapest = min(available_options, key=lambda option: option["unit_price_usd"])
    best_quality = max(
        available_options,
        key=lambda option: (
            option["quality_score"],
            option["supplier_rating"],
            -option["unit_price_usd"],
        ),
    )
    balanced = max(
        available_options,
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
) -> dict[str, Any]:
    item_name = requested_item["name"]
    quantity = int(requested_item["quantity"])

    matches = find_supplier_matches(item_name, catalog)
    options = [
        _build_supplier_option(quantity, match)
        for match in matches
    ]

    recommendations = _select_recommendations(options)

    issues: list[str] = []
    alternatives: list[dict[str, Any]] = []

    if not matches:
        issues.append(f"{item_name}: no supplier match found.")
        alternatives = find_alternatives(item_name, catalog)

    elif not any(option["availability_status"] == "available" for option in options):
        issues.append(
            f"{item_name}: suppliers found, but none can satisfy quantity/MOQ/stock requirements."
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

    item_results = [
        evaluate_shopping_item(item, catalog)
        for item in requested_items
    ]

    selected_items = []
    total_procurement_cost = 0.0

    for result in item_results:
        balanced = result["recommendations"].get("balanced")

        if balanced:
            selected_items.append(balanced)
            total_procurement_cost += balanced["estimated_total_cost_usd"]

    all_issues = [
        issue
        for result in item_results
        for issue in result["issues"]
    ]

    if all_issues:
        status = "partial_plan_needs_more_information"
    elif not selected_items:
        status = "needs_more_information"
    else:
        status = "ready_for_review"

    return {
        "request_context": {
            "request_id": request_data.get("request_id"),
            "customer": request_data.get("customer"),
            "destination_country": request_data.get("destination_country"),
            "preferred_currency": request_data.get("preferred_currency", "USD"),
        },
        "item_results": item_results,
        "selected_items": selected_items,
        "procurement_summary": {
            "selected_supplier_count": len(selected_items),
            "estimated_total_procurement_cost_usd": round(total_procurement_cost, 2),
            "currency": "USD",
        },
        "issues": all_issues,
        "catalog_size": len(catalog),
        "status": status,
    }
