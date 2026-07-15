from __future__ import annotations

import os
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


def _use_trained_router() -> bool:
    return os.environ.get("USE_TRAINED_ROUTER", "0").lower() in {"1", "true", "yes"}


def _route_text_request(text: str) -> dict[str, Any]:
    if not _use_trained_router():
        return detect_text_intent(text)

    try:
        from app.trained_router_backend import predict_trained_route

        decision = predict_trained_route(text)

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


def _attach_final_verdict(response: dict[str, Any]) -> dict[str, Any]:
    final_verdict = derive_final_verdict(response)
    response["final_verdict"] = final_verdict

    if "FINAL VERDICT" not in response["final_answer"]:
        response["final_answer"] = (
            response["final_answer"]
            + "\n\n"
            + format_final_verdict(final_verdict)
        )

    return response


def _build_partner_review_payload(
    logistics_input: dict[str, Any],
    logistics_handoff: dict[str, Any],
    source_handoff: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "request_id": (
            source_handoff.get("request_id")
            or logistics_input.get("shipment_id")
            or logistics_handoff.get("shipment_id")
        ),
        "origin": (
            source_handoff.get("origin_country")
            or logistics_input.get("origin")
            or logistics_handoff.get("origin")
        ),
        "destination": (
            source_handoff.get("destination_country")
            or logistics_input.get("destination")
            or logistics_handoff.get("destination")
        ),
        "total_cbm": logistics_handoff.get("total_cbm"),
        "total_weight_kg": logistics_handoff.get("total_weight_kg"),
        "declared_value_usd": (
            source_handoff.get("total_value")
            or source_handoff.get("estimated_total_procurement_cost_usd")
            or logistics_handoff.get("declared_value_usd")
        ),
    }

    if source_handoff.get("selected_items"):
        payload["selected_items"] = source_handoff["selected_items"]
    else:
        payload["items"] = logistics_input.get("items", source_handoff.get("items", []))

    return payload


def _attach_partner_review(
    response: dict[str, Any],
    logistics_input: dict[str, Any],
    logistics_handoff: dict[str, Any],
    source_handoff: dict[str, Any],
) -> dict[str, Any]:
    partner_payload = _build_partner_review_payload(
        logistics_input=logistics_input,
        logistics_handoff=logistics_handoff,
        source_handoff=source_handoff,
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
        + "\n\nPARTNER REVIEW PLACEHOLDER\n"
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


def _build_shopping_to_logistics_response(
    shopping_response: dict[str, Any],
    detected_intent: str,
    summary: str,
    route_reason: str,
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
    logistics_response = run_logistics_agent(logistics_input)

    combined_status = _combine_statuses(
        [
            shopping_response["status"],
            logistics_response["status"],
        ]
    )

    missing_information = [
        *shopping_response.get("missing_information", []),
        *logistics_response.get("missing_information", []),
    ]

    response = _build_user_agent_response(
        status=combined_status,
        summary="User Agent routed the request to Shopping Agent, then handed selected items to the Logistics Agent.",
        detected_intent=detected_intent,
        agents_called=["shopping_agent", "logistics_agent"],
        specialist_response=shopping_response,
        missing_information=missing_information,
        route_reason=route_reason,
    )

    response["specialist_responses"] = {
        "shopping_agent": shopping_response,
        "logistics_agent": logistics_response,
    }
    response["logistics_input"] = logistics_input
    response["handoff_payload"] = logistics_response.get("handoff_payload", {})
    response["handoff_requests"] = logistics_response.get("handoff_requests", [])
    response["final_answer"] = (
        f"{_build_final_answer(shopping_response)}\n\n"
        f"{_build_final_answer(logistics_response)}"
    )

    return _attach_partner_review(
        response=response,
        logistics_input=logistics_input,
        logistics_handoff=logistics_response.get("handoff_payload", {}),
        source_handoff=shopping_response.get("handoff_payload", {}),
    )


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

            combined_status = _combine_statuses(
                [
                    document_response["status"],
                    logistics_response["status"],
                ]
            )

            missing_information = [
                *document_response.get("missing_information", []),
                *logistics_response.get("missing_information", []),
            ]

            response = _build_user_agent_response(
                status=combined_status,
                summary="User Agent routed the documents to Document AI, then handed the validated cargo data to the Logistics Agent.",
                detected_intent=detected_intent,
                agents_called=["document_ai_agent", "logistics_agent"],
                specialist_response=document_response,
                missing_information=missing_information,
                route_reason="The files were valid trade documents with consistent invoice and packing list cargo data.",
            )

            response["specialist_responses"] = {
                "document_ai_agent": document_response,
                "logistics_agent": logistics_response,
            }
            response["logistics_input"] = logistics_input
            response["handoff_payload"] = logistics_response.get("handoff_payload", {})
            response["handoff_requests"] = logistics_response.get("handoff_requests", [])
            response["final_answer"] = (
                f"{_build_final_answer(document_response)}\n\n"
                f"{_build_final_answer(logistics_response)}"
            )

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

