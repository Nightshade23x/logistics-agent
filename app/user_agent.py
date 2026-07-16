from __future__ import annotations

import os
import re
from app.text_request_intent import classify_text_request_intent
from app.shopping_service import run_shopping_agent_from_text

from pathlib import Path
from typing import Any

from app.agent_router import (
    detect_file_intent,
    detect_json_intent,
    detect_text_intent,
    read_json_file,
)
from app.document_ai_router import run_document_ai_agent
from app.final_verdict import derive_final_verdict, format_final_verdict
from app.logistics_service import run_logistics_agent
from app.partner_review_service import run_partner_review
from app.shopping_service import run_shopping_agent, run_shopping_agent_from_text
from app.trader_adapter import run_trader_agent


def _use_trained_router() -> bool:
    return os.environ.get("USE_TRAINED_ROUTER", "0").lower() in {"1", "true", "yes"}



def _looks_like_shopping_plus_logistics_request(text: str) -> bool:
    """Guardrail for prompts that mention both sourcing and shipping."""

    lowered = text.lower()

    shopping_markers = [
        "find supplier",
        "get supplier",
        "source supplier",
        "supplier for",
        "source ",
        "buy ",
        "purchase ",
        "procure ",
        "vendor",
        "manufacturer",
    ]

    logistics_markers = [
        "freight",
        "shipping",
        "ship ",
        "shipment",
        "container",
        "logistics",
        "lcl",
        "fcl",
        "cbm",
        "from ",
        " to ",
    ]

    return any(marker in lowered for marker in shopping_markers) and any(
        marker in lowered for marker in logistics_markers
    )

def _route_text_request(text: str) -> dict[str, Any]:
    if not _use_trained_router():
        return detect_text_intent(text)

    try:
        from app.trained_router_backend import predict_trained_route

        decision = predict_trained_route(text)

        if _looks_like_shopping_plus_logistics_request(text):
            decision = dict(decision)
            decision["intent"] = "shopping"
            decision["agents_to_call"] = ["shopping_agent", "logistics_agent"]
            decision["input_type"] = "text"
            decision["confidence"] = "high"
            decision["reason"] = (
                "Deterministic guardrail: request includes both supplier sourcing "
                "and shipping/logistics intent."
            )
        elif _looks_like_direct_trader_request(text):
            decision = dict(decision)
            decision["intent"] = "trader"
            decision["agents_to_call"] = ["trader_agent"]
            decision["input_type"] = "text"
            decision["confidence"] = "high"
            decision["reason"] = (
                "Deterministic guardrail: request asks for trade, tariff, duty, "
                "FTA, HS code, customs, or export strategy assessment."
            )

        return {
            "detected_intent": decision.get("intent", "unknown"),
            "scores": {},
            "source": "trained_router",
            "trained_router_decision": decision,
        }

    except Exception as error:
        fallback = detect_text_intent(text)
        fallback["source"] = "rule_based_fallback"
        fallback["trained_router_error"] = str(error)
        return fallback


def _build_final_answer(agent_response: dict[str, Any]) -> str:
    return (
        f"{agent_response['summary']}\n\n"
        f"{agent_response['report']}"
    )


def _build_user_agent_response(
    status: str,
    summary: str,
    detected_intent: str,
    agents_called: list[str],
    specialist_response: dict[str, Any] | None,
    missing_information: list[str] | None = None,
    route_reason: str | None = None,
) -> dict[str, Any]:
    missing_information = missing_information or []

    if specialist_response:
        final_answer = _build_final_answer(specialist_response)
        handoff_payload = specialist_response.get("handoff_payload", {})
        handoff_requests = specialist_response.get("handoff_requests", [])
    else:
        final_answer = summary
        handoff_payload = {}
        handoff_requests = []

    return {
        "agent_name": "user_agent",
        "status": status,
        "summary": summary,
        "detected_intent": detected_intent,
        "agents_called": agents_called,
        "route_reason": route_reason,
        "final_answer": final_answer,
        "specialist_response": specialist_response,
        "missing_information": missing_information,
        "handoff_payload": handoff_payload,
        "handoff_requests": handoff_requests,
    }



PARTNER_REVIEW_OBSERVABILITY_FIELDS = (
    "partner_review_attempted",
    "partner_review_mode",
    "partner_review_service_called",
    "live_orchestrator_configured",
)


def _get_partner_review_response(response: dict[str, Any]) -> dict[str, Any]:
    partner_review = response.get("partner_review")
    if isinstance(partner_review, dict):
        return partner_review

    specialist_responses = response.get("specialist_responses")
    if isinstance(specialist_responses, dict):
        partner_response = specialist_responses.get("partner_review_service")
        if isinstance(partner_response, dict):
            return partner_response

    return {}


def _sync_partner_review_observability(response: dict[str, Any]) -> dict[str, Any]:
    """Expose nested partner-review observability fields at User Agent top level."""

    partner_response = _get_partner_review_response(response)
    if not partner_response:
        return response

    if response.get("partner_review_status") is None and partner_response.get("status") is not None:
        response["partner_review_status"] = partner_response.get("status")

    for field in PARTNER_REVIEW_OBSERVABILITY_FIELDS:
        if response.get(field) is None and partner_response.get(field) is not None:
            response[field] = partner_response.get(field)

    review_services = response.get("review_services_called")
    if review_services is None:
        response["review_services_called"] = ["partner_review_service"]
    elif isinstance(review_services, list) and "partner_review_service" not in review_services:
        review_services.append("partner_review_service")

    return response


def _attach_final_verdict(response: dict[str, Any]) -> dict[str, Any]:
    _sync_partner_review_observability(response)
    final_verdict = derive_final_verdict(response)
    response["final_verdict"] = final_verdict

    if "FINAL VERDICT" not in response["final_answer"]:
        response["final_answer"] = (
            response["final_answer"]
            + "\n\n"
            + format_final_verdict(final_verdict)
        )

    return response



def _has_partner_payload_value(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, dict)):
        return bool(value)

    return True


def _first_partner_payload_value(*values: Any) -> Any:
    for value in values:
        if _has_partner_payload_value(value):
            return value

    return None


def _parse_float_from_text(value: str | None) -> float | None:
    if not value:
        return None

    try:
        return float(value.replace(",", "").strip())
    except ValueError:
        return None


def _extract_trade_cost_fields_from_text(text: str | None) -> dict[str, Any]:
    if not text:
        return {}

    fields: dict[str, Any] = {}

    incoterm_codes = "EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP"

    incoterm_patterns = [
        rf"\b(?:use\s+)?({incoterm_codes})\s+incoterm\b",
        rf"\bincoterm\s*(?:is|=|:)?\s*({incoterm_codes})\b",
    ]

    for pattern in incoterm_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            fields["incoterm"] = match.group(1).upper()
            break

    numeric_patterns = {
        "freight_quote_usd": [
            r"\bfreight\s+quote\s*(?:is|=|:)?\s*(?:USD|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:USD|dollars?)?\b",
            r"\bfreight\s+cost\s*(?:is|=|:)?\s*(?:USD|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:USD|dollars?)?\b",
        ],
        "insurance_premium_usd": [
            r"\binsurance\s+premium\s*(?:is|=|:)?\s*(?:USD|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:USD|dollars?)?\b",
            r"\binsurance\s+cost\s*(?:is|=|:)?\s*(?:USD|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:USD|dollars?)?\b",
        ],
        "duty_rate_percent": [
            r"\bduty\s+rate\s*(?:is|=|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:percent|%)\b",
            r"\bimport\s+duty\s*(?:is|=|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:percent|%)\b",
        ],
        "import_tax_rate_percent": [
            r"\bimport\s+tax\s+rate\s*(?:is|=|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:percent|%)\b",
            r"\btax\s+rate\s*(?:is|=|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:percent|%)\b",
        ],
    }

    for field, patterns in numeric_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                parsed = _parse_float_from_text(match.group(1))
                if parsed is not None:
                    fields[field] = parsed
                    break

    return fields


def _copy_partner_payload_optional_fields(
    payload: dict[str, Any],
    *sources: dict[str, Any],
) -> None:
    aliases = {
        "incoterm": ("incoterm", "trade_term"),
        "freight_quote_usd": ("freight_quote_usd", "freight_quote", "freight_cost_usd"),
        "insurance_premium_usd": (
            "insurance_premium_usd",
            "insurance_premium",
            "insurance_cost_usd",
        ),
        "duty_rate_percent": ("duty_rate_percent", "duty_rate"),
        "import_tax_rate_percent": ("import_tax_rate_percent", "import_tax_rate"),
    }

    for output_key, input_keys in aliases.items():
        if _has_partner_payload_value(payload.get(output_key)):
            continue

        for source in sources:
            if not isinstance(source, dict):
                continue

            for input_key in input_keys:
                value = source.get(input_key)
                if _has_partner_payload_value(value):
                    payload[output_key] = value
                    break

            if _has_partner_payload_value(payload.get(output_key)):
                break


def _build_partner_review_payload(
    logistics_input: dict[str, Any],
    logistics_handoff: dict[str, Any],
    source_handoff: dict[str, Any],
    original_text: str | None = None,
) -> dict[str, Any]:
    extract_route = globals().get("_extract_route_from_text")
    route_from_text = (
        extract_route(original_text)
        if callable(extract_route)
        else {"country_from": None, "country_to": None}
    )

    origin = _first_partner_payload_value(
        source_handoff.get("origin_country"),
        source_handoff.get("origin"),
        logistics_input.get("origin_country"),
        logistics_input.get("origin"),
        logistics_handoff.get("origin_country"),
        logistics_handoff.get("origin"),
        route_from_text.get("country_from"),
    )

    destination = _first_partner_payload_value(
        source_handoff.get("destination_country"),
        source_handoff.get("destination"),
        logistics_input.get("destination_country"),
        logistics_input.get("destination"),
        logistics_handoff.get("destination_country"),
        logistics_handoff.get("destination"),
        route_from_text.get("country_to"),
    )

    normalizer = globals().get("_normalize_country_name")
    if callable(normalizer):
        if origin:
            origin = normalizer(str(origin))
        if destination:
            destination = normalizer(str(destination))

    payload = {
        "request_id": (
            source_handoff.get("request_id")
            or logistics_input.get("shipment_id")
            or logistics_handoff.get("shipment_id")
        ),
        "origin": origin,
        "origin_country": origin,
        "destination": destination,
        "destination_country": destination,
        "total_cbm": _first_partner_payload_value(
            logistics_handoff.get("total_cbm"),
            logistics_input.get("total_cbm"),
            source_handoff.get("total_cbm"),
        ),
        "total_weight_kg": _first_partner_payload_value(
            logistics_handoff.get("total_weight_kg"),
            logistics_input.get("total_weight_kg"),
            source_handoff.get("total_weight_kg"),
        ),
        "declared_value_usd": _first_partner_payload_value(
            source_handoff.get("total_value"),
            source_handoff.get("estimated_total_procurement_cost_usd"),
            logistics_input.get("declared_value_usd"),
            logistics_handoff.get("declared_value_usd"),
        ),
    }

    selected_items = _first_partner_payload_value(
        source_handoff.get("selected_items"),
        logistics_input.get("selected_items"),
    )

    if selected_items:
        payload["selected_items"] = selected_items
    else:
        payload["items"] = _first_partner_payload_value(
            logistics_input.get("items"),
            source_handoff.get("items"),
            logistics_handoff.get("items"),
            [],
        )

    _copy_partner_payload_optional_fields(
        payload,
        source_handoff,
        logistics_input,
        logistics_handoff,
    )

    payload.update(_extract_trade_cost_fields_from_text(original_text))

    return payload


def _attach_partner_review(
    response: dict[str, Any],
    logistics_input: dict[str, Any],
    logistics_handoff: dict[str, Any],
    source_handoff: dict[str, Any],
    original_text: str | None = None,
) -> dict[str, Any]:
    partner_payload = _build_partner_review_payload(
        logistics_input=logistics_input,
        logistics_handoff=logistics_handoff,
        source_handoff=source_handoff,
        original_text=original_text,
    )

    partner_review = run_partner_review(
        partner_payload,
        request_id=partner_payload.get("request_id"),
    )

    response.setdefault("review_services_called", [])

    if "partner_review_service" not in response["review_services_called"]:
        response["review_services_called"].append("partner_review_service")

    response.setdefault("specialist_responses", {})
    response["specialist_responses"]["partner_review_service"] = partner_review
    response["partner_review"] = partner_review
    response["partner_review_payload"] = partner_payload
    response["partner_review_status"] = partner_review.get("status")

    response["final_answer"] = (
        response["final_answer"]
        + "\n\nPARTNER REVIEW\n"
        + "------------------------------\n"
        + f"Status: {partner_review.get('status')}\n"
        + f"{partner_review.get('summary')}"
    )

    return _attach_final_verdict(response)


def _shopping_handoff_to_logistics_input(
    handoff_payload: dict[str, Any],
) -> dict[str, Any]:
    selected_items = handoff_payload.get("selected_items", [])
    supplier_countries = handoff_payload.get("supplier_countries", [])

    if len(supplier_countries) == 1:
        origin = supplier_countries[0]
    elif len(supplier_countries) > 1:
        origin = "Multiple supplier countries"
    else:
        origin = None

    items = []

    for item in selected_items:
        items.append(
            {
                "name": item.get("product_name"),
                "quantity": item.get("requested_quantity", 1),
            }
        )

    return {
        "shipment_id": f"SHOP-{handoff_payload.get('request_id', 'GENERATED-SHIPMENT')}",
        "customer": handoff_payload.get("customer"),
        "origin": origin,
        "destination": handoff_payload.get("destination_country"),
        "notes": "Shipment data generated from Shopping Agent selected supplier items.",
        "items": items,
    }


def _can_handoff_shopping_to_logistics(
    shopping_response: dict[str, Any],
) -> bool:
    handoff_payload = shopping_response.get("handoff_payload", {})
    selected_items = handoff_payload.get("selected_items", [])

    return (
        shopping_response.get("status") in {"ready_for_review", "review_required"}
        and bool(selected_items)
    )


def _use_trader_agent() -> bool:
    return os.environ.get("ENABLE_TRADER_AGENT", "0").lower() in {"1", "true", "yes"}


def _first(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return value


def _first_item_name(items: Any) -> str | None:
    if isinstance(items, list) and items:
        first_item = items[0]
        if isinstance(first_item, dict):
            return (
                first_item.get("product_name")
                or first_item.get("name")
                or first_item.get("item_name")
                or first_item.get("description")
            )
        return str(first_item)

    return None




def _normalize_country_name(value: str | None) -> str | None:
    if not value:
        return value

    cleaned = value.strip()
    upper = cleaned.upper()

    common = {
        "USA": "USA",
        "US": "USA",
        "U.S.": "USA",
        "U.S.A.": "USA",
        "UK": "UK",
        "U.K.": "UK",
        "UAE": "UAE",
        "EU": "EU",
    }

    return common.get(upper, cleaned.title())

def _extract_route_from_text(text: str | None) -> dict[str, str | None]:
    if not text:
        return {"country_from": None, "country_to": None}

    match = re.search(
        r"\bfrom\s+([A-Za-z][A-Za-z\s]+?)\s+to\s+([A-Za-z][A-Za-z\s]+?)(?:\.|,|$|\s+for|\s+with|\s+and)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return {"country_from": None, "country_to": None}

    return {
        "country_from": _normalize_country_name(match.group(1)),
        "country_to": _normalize_country_name(match.group(2)),
    }

def _build_trader_input_from_handoffs(
    shopping_response: dict[str, Any],
    logistics_input: dict[str, Any],
    logistics_response: dict[str, Any],
    original_text: str | None = None,
) -> dict[str, Any]:
    shopping_handoff = shopping_response.get("handoff_payload", {})
    logistics_handoff = logistics_response.get("handoff_payload", {})
    route_from_text = _extract_route_from_text(original_text)

    selected_items = shopping_handoff.get("selected_items") or shopping_handoff.get("items") or []
    logistics_items = logistics_input.get("items", [])

    product_description = (
        _first_item_name(selected_items)
        or _first_item_name(logistics_items)
        or shopping_handoff.get("product_description")
        or shopping_handoff.get("product_name")
    )

    country_from = (
        _first(shopping_handoff.get("supplier_countries"))
        or shopping_handoff.get("origin_country")
        or logistics_input.get("origin_country")
        or logistics_handoff.get("origin_country")
        or route_from_text.get("country_from")
    )

    country_to = (
        shopping_handoff.get("destination_country")
        or logistics_input.get("destination_country")
        or logistics_handoff.get("destination_country")
        or route_from_text.get("country_to")
    )

    return {
        "product_description": product_description,
        "country_from": country_from,
        "country_to": country_to,
        "target_market": country_to,
    }



def _apply_text_route_to_logistics_input(logistics_input: dict[str, Any], original_text: str | None) -> dict[str, Any]:
    """Fill origin/destination in logistics input from original user text when available."""
    if not isinstance(logistics_input, dict):
        return logistics_input

    route = _extract_route_from_text(original_text or "")
    country_from = route.get("country_from")
    country_to = route.get("country_to")

    if country_from and not logistics_input.get("origin"):
        logistics_input["origin"] = country_from
    if country_from and not logistics_input.get("origin_country"):
        logistics_input["origin_country"] = country_from

    if country_to and not logistics_input.get("destination"):
        logistics_input["destination"] = country_to
    if country_to and not logistics_input.get("destination_country"):
        logistics_input["destination_country"] = country_to

    return logistics_input

def _build_shopping_to_logistics_response(
    shopping_response: dict[str, Any],
    detected_intent: str,
    summary: str,
    route_reason: str,
    original_text: str | None = None,
) -> dict[str, Any]:
    if not _can_handoff_shopping_to_logistics(shopping_response):
        return _build_user_agent_response(
            status=shopping_response["status"],
            summary=summary,
            detected_intent=detected_intent,
            agents_called=["shopping_agent"],
            specialist_response=shopping_response,
            missing_information=shopping_response.get("missing_information", []),
            route_reason=route_reason,
        )

    logistics_input = _shopping_handoff_to_logistics_input(
        shopping_response.get("handoff_payload", {})
    )
    logistics_input = _apply_text_route_to_logistics_input(logistics_input, original_text)
    logistics_response = run_logistics_agent(logistics_input)

    agents_called = ["shopping_agent", "logistics_agent"]
    specialist_responses = {
        "shopping_agent": shopping_response,
        "logistics_agent": logistics_response,
    }

    statuses = [
        shopping_response["status"],
        logistics_response["status"],
    ]

    missing_information = [
        *shopping_response.get("missing_information", []),
        *logistics_response.get("missing_information", []),
    ]

    handoff_requests = [
        *logistics_response.get("handoff_requests", []),
    ]

    trader_input: dict[str, Any] | None = None
    trader_response: dict[str, Any] | None = None

    if _use_trader_agent():
        trader_input = _build_trader_input_from_handoffs(
            shopping_response=shopping_response,
            logistics_input=logistics_input,
            logistics_response=logistics_response,
            original_text=original_text,
        )
        trader_response = run_trader_agent(trader_input, use_reasoning=True)

        agents_called.append("trader_agent")
        specialist_responses["trader_agent"] = trader_response
        statuses.append(trader_response.get("status", "review_required"))
        missing_information.extend(trader_response.get("missing_information", []))
        handoff_requests.extend(trader_response.get("handoff_requests", []))

    combined_status = _combine_statuses(statuses)

    if trader_response:
        response_summary = (
            "User Agent routed the request to Shopping Agent, handed selected items "
            "to the Logistics Agent, then ran Trader Agent trade assessment."
        )
    else:
        response_summary = (
            "User Agent routed the request to Shopping Agent, then handed selected "
            "items to the Logistics Agent."
        )

    response = _build_user_agent_response(
        status=combined_status,
        summary=response_summary,
        detected_intent=detected_intent,
        agents_called=agents_called,
        specialist_response=shopping_response,
        missing_information=missing_information,
        route_reason=route_reason,
    )

    response["specialist_responses"] = specialist_responses
    response["logistics_input"] = logistics_input
    response["handoff_payload"] = logistics_response.get("handoff_payload", {})
    response["handoff_requests"] = handoff_requests

    if trader_input is not None:
        response["trader_input"] = trader_input

    if trader_response is not None:
        response["trader_handoff_payload"] = trader_response.get("handoff_payload", {})

    final_parts = [
        _build_final_answer(shopping_response),
        _build_final_answer(logistics_response),
    ]

    if trader_response is not None:
        final_parts.append(_build_final_answer(trader_response))

    response["final_answer"] = "\n\n".join(final_parts)

    return _attach_partner_review(
        response=response,
        logistics_input=logistics_input,
        logistics_handoff=logistics_response.get("handoff_payload", {}),
        source_handoff=shopping_response.get("handoff_payload", {}),
        original_text=original_text,
    )



def _build_trader_input_from_document_handoff(
    document_handoff: dict[str, Any],
    logistics_input: dict[str, Any],
    logistics_response: dict[str, Any],
) -> dict[str, Any]:
    logistics_handoff = logistics_response.get("handoff_payload", {})

    items = (
        document_handoff.get("items")
        or logistics_input.get("items")
        or logistics_handoff.get("items")
        or []
    )

    product_description = _first_item_name(items)

    country_from = (
        document_handoff.get("origin_country")
        or logistics_input.get("origin_country")
        or logistics_handoff.get("origin_country")
    )

    country_to = (
        document_handoff.get("destination_country")
        or logistics_input.get("destination_country")
        or logistics_handoff.get("destination_country")
    )

    return {
        "product_description": product_description,
        "country_from": country_from,
        "country_to": country_to,
        "target_market": country_to,
    }


def _looks_like_direct_trader_request(text: str) -> bool:
    lowered = text.lower()

    trader_markers = [
        "trade plan",
        "assess trade",
        "trade assessment",
        "hs code",
        "hscode",
        "tariff",
        "duty",
        "duties",
        "customs",
        "fta",
        "free trade agreement",
        "export strategy",
        "import duty",
    ]

    return any(marker in lowered for marker in trader_markers)


def _extract_product_from_trade_text(text: str) -> str | None:
    patterns = [
        r"\b(?:for|of)\s+(.+?)\s+from\s+[A-Za-z][A-Za-z\s]+?\s+to\s+[A-Za-z][A-Za-z\s]+",
        r"\b(?:for|of)\s+(.+?)(?:\.|,|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            product = match.group(1).strip()
            product = re.sub(
                r"^(trade plan|hs code|hscode|tariff|duty|duties|customs|fta|export strategy)\s+",
                "",
                product,
                flags=re.IGNORECASE,
            ).strip()
            return product or None

    return None


def _build_trader_input_from_text(text: str) -> dict[str, Any]:
    route = _extract_route_from_text(text)

    return {
        "product_description": _extract_product_from_trade_text(text),
        "country_from": route.get("country_from"),
        "country_to": route.get("country_to"),
        "target_market": route.get("country_to"),
    }

def run_user_agent_from_text(text: str) -> dict[str, Any]:
    routing = _route_text_request(text)
    detected_intent = routing["detected_intent"]

    if detected_intent == "shopping":
        shopping_response = run_shopping_agent_from_text(text)

        trained_decision = routing.get("trained_router_decision") or {}
        requested_agents = trained_decision.get("agents_to_call")

        should_call_logistics = True

        if routing.get("source") == "trained_router" and isinstance(requested_agents, list):
            should_call_logistics = "logistics_agent" in requested_agents

        route_reason = trained_decision.get(
            "reason",
            "The request contains supplier, purchasing, budget, or product sourcing language.",
        )

        if should_call_logistics:
            response = _build_shopping_to_logistics_response(
                shopping_response=shopping_response,
                detected_intent=detected_intent,
                summary="User Agent routed the request to the Shopping Agent.",
                route_reason=route_reason,
                original_text=text,
            )
        else:
            response = _build_user_agent_response(
                status=shopping_response.get("status", "review_required"),
                summary="User Agent routed the request to the Shopping Agent.",
                detected_intent=detected_intent,
                agents_called=["shopping_agent"],
                specialist_response=shopping_response,
                missing_information=shopping_response.get("missing_information", []),
                route_reason=route_reason,
            )

        response["router_source"] = routing.get("source")
        response["trained_router_decision"] = routing.get("trained_router_decision")

        return response

    if detected_intent == "trader":
        trader_input = _build_trader_input_from_text(text)
        trader_response = run_trader_agent(trader_input, use_reasoning=True)

        response = _build_user_agent_response(
            status=trader_response.get("status", "review_required"),
            summary="User Agent routed the request directly to Trader Agent.",
            detected_intent=detected_intent,
            agents_called=["trader_agent"],
            specialist_response=trader_response,
            missing_information=trader_response.get("missing_information", []),
            route_reason=routing.get("trained_router_decision", {}).get(
                "reason",
                "The request contains trade, customs, tariff, duty, FTA, or HS code language.",
            ),
        )

        response["specialist_responses"] = {
            "trader_agent": trader_response,
        }
        response["trader_input"] = trader_input
        response["handoff_payload"] = trader_response.get("handoff_payload", {})
        response["handoff_requests"] = trader_response.get("handoff_requests", [])
        response["final_answer"] = _build_final_answer(trader_response)
        response["router_source"] = routing.get("source")
        response["trained_router_decision"] = routing.get("trained_router_decision")

        return _attach_final_verdict(response)

    if detected_intent == "logistics":
        response = _build_user_agent_response(
            status="needs_more_information",
            summary="User Agent detected a logistics request, but V1 requires logistics requests as structured JSON.",
            detected_intent=detected_intent,
            agents_called=[],
            specialist_response=None,
            missing_information=["structured_logistics_json"],
            route_reason=routing.get("trained_router_decision", {}).get(
                "reason",
                "The request contains shipping, container, CBM, or cargo language.",
            ),
        )

        response["router_source"] = routing.get("source")
        response["trained_router_decision"] = routing.get("trained_router_decision")

        return response

    if detected_intent == "document":
        response = _build_user_agent_response(
            status="needs_more_information",
            summary="User Agent detected a document request. Please provide document file paths for Document AI.",
            detected_intent=detected_intent,
            agents_called=[],
            specialist_response=None,
            missing_information=["document_file_paths"],
            route_reason=routing.get("trained_router_decision", {}).get(
                "reason",
                "The request contains invoice, packing list, bill of lading, or certificate language.",
            ),
        )

        response["router_source"] = routing.get("source")
        response["trained_router_decision"] = routing.get("trained_router_decision")

        return response

    response = _build_user_agent_response(
        status="needs_more_information",
        summary="User Agent could not confidently detect the request type.",
        detected_intent="unknown",
        agents_called=[],
        specialist_response=None,
        missing_information=["clearer_user_request"],
        route_reason=routing.get("trained_router_decision", {}).get(
            "reason",
            "No strong routing keywords were detected.",
        ),
    )

    response["router_source"] = routing.get("source")
    response["trained_router_decision"] = routing.get("trained_router_decision")

    return response


def _combine_statuses(statuses: list[str]) -> str:
    priority = {
        "error": 6,
        "blocked": 6,
        "critical_review_required": 5,
        "needs_more_information": 4,
        "partial_plan_needs_more_information": 4,
        "review_required": 3,
        "ready_for_review": 1,
    }

    return max(statuses, key=lambda status: priority.get(status, 0))


def _document_handoff_to_logistics_input(
    handoff_payload: dict[str, Any],
) -> dict[str, Any]:
    invoice_fields = handoff_payload.get("invoice_fields", {})
    packing_list_fields = handoff_payload.get("packing_list_fields", {})

    shipment_id = (
        invoice_fields.get("invoice_number")
        or packing_list_fields.get("packing_list_number")
        or "DOC-GENERATED-SHIPMENT"
    )

    items = []

    for item in handoff_payload.get("items", []):
        dimension_unit = str(item.get("dimension_unit", "cm")).lower()
        weight_unit = str(item.get("weight_unit", "kg")).lower()

        logistics_item = {
            "name": item.get("name"),
            "quantity": item.get("quantity", 1),
        }

        if dimension_unit in {"cm", "centimeter", "centimeters"}:
            logistics_item["length_cm"] = item.get("length")
            logistics_item["width_cm"] = item.get("width")
            logistics_item["height_cm"] = item.get("height")
        else:
            logistics_item["length"] = item.get("length")
            logistics_item["width"] = item.get("width")
            logistics_item["height"] = item.get("height")
            logistics_item["dimension_unit"] = dimension_unit

        if weight_unit in {"kg", "kilogram", "kilograms"}:
            logistics_item["weight_kg"] = item.get("weight")
        else:
            logistics_item["weight"] = item.get("weight")
            logistics_item["weight_unit"] = weight_unit

        items.append(logistics_item)

    return {
        "shipment_id": f"DOC-{shipment_id}",
        "customer": invoice_fields.get("buyer"),
        "origin": handoff_payload.get("origin_country"),
        "destination": handoff_payload.get("destination_country"),
        "notes": "Shipment data generated from Document AI validated invoice and packing list.",
        "items": items,
    }


def run_user_agent_from_files(paths: list[str | Path]) -> dict[str, Any]:
    routing = detect_file_intent(paths)
    detected_intent = routing["detected_intent"]

    if detected_intent == "document":
        document_response = run_document_ai_agent(paths)
        document_handoff = document_response.get("handoff_payload", {})
        mismatch_count = document_handoff.get("mismatch_count", 0)
        document_items = document_handoff.get("items", [])

        can_handoff_to_logistics = (
            document_response.get("status") in {"ready_for_review", "review_required"}
            and mismatch_count == 0
            and bool(document_items)
        )

        if can_handoff_to_logistics:
            logistics_input = _document_handoff_to_logistics_input(document_handoff)
            logistics_response = run_logistics_agent(logistics_input)

            agents_called = ["document_ai_agent", "logistics_agent"]
            specialist_responses = {
                "document_ai_agent": document_response,
                "logistics_agent": logistics_response,
            }

            statuses = [
                document_response["status"],
                logistics_response["status"],
            ]

            missing_information = [
                *document_response.get("missing_information", []),
                *logistics_response.get("missing_information", []),
            ]

            handoff_requests = [
                *logistics_response.get("handoff_requests", []),
            ]

            trader_input = None
            trader_response = None

            if _use_trader_agent():
                trader_input = _build_trader_input_from_document_handoff(
                    document_handoff=document_handoff,
                    logistics_input=logistics_input,
                    logistics_response=logistics_response,
                )
                trader_response = run_trader_agent(trader_input, use_reasoning=True)

                agents_called.append("trader_agent")
                specialist_responses["trader_agent"] = trader_response
                statuses.append(trader_response.get("status", "review_required"))
                missing_information.extend(trader_response.get("missing_information", []))
                handoff_requests.extend(trader_response.get("handoff_requests", []))

            combined_status = _combine_statuses(statuses)

            if trader_response:
                response_summary = (
                    "User Agent routed the documents to Document AI, handed the "
                    "validated cargo data to the Logistics Agent, then ran Trader "
                    "Agent trade assessment."
                )
            else:
                response_summary = (
                    "User Agent routed the documents to Document AI, then handed "
                    "the validated cargo data to the Logistics Agent."
                )

            response = _build_user_agent_response(
                status=combined_status,
                summary=response_summary,
                detected_intent=detected_intent,
                agents_called=agents_called,
                specialist_response=document_response,
                missing_information=missing_information,
                route_reason="The files were valid trade documents with consistent invoice and packing list cargo data.",
            )

            response["specialist_responses"] = specialist_responses
            response["logistics_input"] = logistics_input
            response["handoff_payload"] = logistics_response.get("handoff_payload", {})
            response["handoff_requests"] = handoff_requests

            if trader_input is not None:
                response["trader_input"] = trader_input

            if trader_response is not None:
                response["trader_handoff_payload"] = trader_response.get("handoff_payload", {})

            final_parts = [
                _build_final_answer(document_response),
                _build_final_answer(logistics_response),
            ]

            if trader_response is not None:
                final_parts.append(_build_final_answer(trader_response))

            response["final_answer"] = "\n\n".join(final_parts)

            return _attach_partner_review(
                response=response,
                logistics_input=logistics_input,
                logistics_handoff=logistics_response.get("handoff_payload", {}),
                source_handoff=document_handoff,
            )

        return _build_user_agent_response(
            status=document_response["status"],
            summary="User Agent routed the uploaded file(s) to the Document AI Agent.",
            detected_intent=detected_intent,
            agents_called=["document_ai_agent"],
            specialist_response=document_response,
            missing_information=document_response.get("missing_information", []),
            route_reason="The provided files look like trade or shipping documents, but they were not ready for Logistics Agent handoff.",
        )

    return _build_user_agent_response(
        status="needs_more_information",
        summary="User Agent could not confidently route the provided files.",
        detected_intent="unknown",
        agents_called=[],
        specialist_response=None,
        missing_information=["supported_document_files"],
        route_reason="File intent was not recognized.",
    )

def run_user_agent_from_json(data: dict[str, Any]) -> dict[str, Any]:
    routing = detect_json_intent(data)
    detected_intent = routing["detected_intent"]

    if detected_intent == "shopping":
        shopping_response = run_shopping_agent(data)

        return _build_shopping_to_logistics_response(
            shopping_response=shopping_response,
            detected_intent=detected_intent,
            summary="User Agent routed the JSON request to the Shopping Agent.",
            route_reason="The JSON request contains shopping/procurement fields.",
        )

    if detected_intent == "logistics":
        logistics_response = run_logistics_agent(data)

        response = _build_user_agent_response(
            status=logistics_response["status"],
            summary="User Agent routed the JSON request to the Logistics Agent.",
            detected_intent=detected_intent,
            agents_called=["logistics_agent"],
            specialist_response=logistics_response,
            missing_information=logistics_response.get("missing_information", []),
            route_reason="The JSON request contains origin, destination, and cargo item fields.",
        )

        response["specialist_responses"] = {
            "logistics_agent": logistics_response,
        }
        response["logistics_input"] = data
        response["handoff_payload"] = logistics_response.get("handoff_payload", {})
        response["handoff_requests"] = logistics_response.get("handoff_requests", [])

        return _attach_partner_review(
            response=response,
            logistics_input=data,
            logistics_handoff=logistics_response.get("handoff_payload", {}),
            source_handoff=data,
        )

    return _build_user_agent_response(
        status="needs_more_information",
        summary="User Agent could not confidently route the JSON request.",
        detected_intent="unknown",
        agents_called=[],
        specialist_response=None,
        missing_information=["clearer_json_request"],
        route_reason="JSON structure did not match a supported specialist agent.",
    )


def run_user_agent_from_json_file(path: str | Path) -> dict[str, Any]:
    data = read_json_file(path)
    response = run_user_agent_from_json(data)
    response["input_source"] = str(path)
    return response

# Text intent fallback wrapper for procurement/logistics-style natural language requests.
# Keeps the original behavior unless the original text route returns unknown.
try:
    _original_run_user_agent_from_text_for_intent_fallback = run_user_agent_from_text

    def run_user_agent_from_text(user_text: str):
        response = _original_run_user_agent_from_text_for_intent_fallback(user_text)

        if not isinstance(response, dict):
            return response

        detected_intent = response.get("detected_intent")

        if detected_intent not in {None, "", "unknown"}:
            return response

        fallback_intent = classify_text_request_intent(user_text)

        if fallback_intent != "shopping":
            return response

        shopping_response = run_shopping_agent_from_text(user_text)

        if not isinstance(shopping_response, dict):
            shopping_response = {
                "agent_name": "shopping_agent",
                "status": "error",
                "summary": "Shopping Agent did not return a dictionary response.",
            }

        return {
            "agent_name": "user_agent",
            "status": shopping_response.get("status", "review_required"),
            "detected_intent": "shopping",
            "agents_called": ["shopping_agent"],
            "summary": "User Agent routed the text request to Shopping Agent using text intent fallback.",
            "specialist_responses": {
                "shopping_agent": shopping_response,
            },
            "missing_information": shopping_response.get("missing_information", []),
            "handoff_payload": shopping_response.get("handoff_payload", {}),
            "handoff_requests": shopping_response.get("handoff_requests", []),
            "final_verdict": {
                "verdict": "review_required",
                "agent_statuses": [shopping_response.get("status", "review_required")],
                "blockers": [],
                "warnings": [
                    "Text fallback routed this request to Shopping Agent only. Logistics and partner review may need to run after structured shipment data is confirmed."
                ],
                "missing_information_count": len(shopping_response.get("missing_information", [])),
                "partner_review_status": None,
                "assumptions_count": 0,
            },
        }

except NameError:
    pass

