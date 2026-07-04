from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agent_router import (
    detect_file_intent,
    detect_json_intent,
    detect_text_intent,
    read_json_file,
)
from app.document_ai_router import run_document_ai_agent
from app.logistics_service import run_logistics_agent
from app.shopping_service import run_shopping_agent, run_shopping_agent_from_text


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


def run_user_agent_from_text(text: str) -> dict[str, Any]:
    routing = detect_text_intent(text)
    detected_intent = routing["detected_intent"]

    if detected_intent == "shopping":
        specialist_response = run_shopping_agent_from_text(text)

        return _build_user_agent_response(
            status=specialist_response["status"],
            summary="User Agent routed the request to the Shopping Agent.",
            detected_intent=detected_intent,
            agents_called=["shopping_agent"],
            specialist_response=specialist_response,
            missing_information=specialist_response.get("missing_information", []),
            route_reason="The request contains supplier, purchasing, budget, or product sourcing language.",
        )

    if detected_intent == "logistics":
        return _build_user_agent_response(
            status="needs_more_information",
            summary="User Agent detected a logistics request, but V1 requires logistics requests as structured JSON.",
            detected_intent=detected_intent,
            agents_called=[],
            specialist_response=None,
            missing_information=["structured_logistics_json"],
            route_reason="The request contains shipping, container, CBM, or cargo language.",
        )

    if detected_intent == "document":
        return _build_user_agent_response(
            status="needs_more_information",
            summary="User Agent detected a document request. Please provide document file paths for Document AI.",
            detected_intent=detected_intent,
            agents_called=[],
            specialist_response=None,
            missing_information=["document_file_paths"],
            route_reason="The request contains invoice, packing list, bill of lading, or certificate language.",
        )

    return _build_user_agent_response(
        status="needs_more_information",
        summary="User Agent could not confidently detect the request type.",
        detected_intent="unknown",
        agents_called=[],
        specialist_response=None,
        missing_information=["clearer_user_request"],
        route_reason="No strong routing keywords were detected.",
    )


def run_user_agent_from_files(paths: list[str | Path]) -> dict[str, Any]:
    routing = detect_file_intent(paths)
    detected_intent = routing["detected_intent"]

    if detected_intent == "document":
        specialist_response = run_document_ai_agent(paths)

        return _build_user_agent_response(
            status=specialist_response["status"],
            summary="User Agent routed the uploaded file(s) to the Document AI Agent.",
            detected_intent=detected_intent,
            agents_called=["document_ai_agent"],
            specialist_response=specialist_response,
            missing_information=specialist_response.get("missing_information", []),
            route_reason="The provided files look like trade or shipping documents.",
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
        specialist_response = run_shopping_agent(data)

        return _build_user_agent_response(
            status=specialist_response["status"],
            summary="User Agent routed the JSON request to the Shopping Agent.",
            detected_intent=detected_intent,
            agents_called=["shopping_agent"],
            specialist_response=specialist_response,
            missing_information=specialist_response.get("missing_information", []),
            route_reason="The JSON request contains shopping/procurement fields.",
        )

    if detected_intent == "logistics":
        specialist_response = run_logistics_agent(data)

        return _build_user_agent_response(
            status=specialist_response["status"],
            summary="User Agent routed the JSON request to the Logistics Agent.",
            detected_intent=detected_intent,
            agents_called=["logistics_agent"],
            specialist_response=specialist_response,
            missing_information=specialist_response.get("missing_information", []),
            route_reason="The JSON request contains origin, destination, and cargo item fields.",
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
