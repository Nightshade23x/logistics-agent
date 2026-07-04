from __future__ import annotations

from pathlib import Path
from typing import Any

from app.document_parser import parse_trade_document, read_document_text
from app.document_service import run_document_agent_from_file
from app.document_pair_service import run_document_pair_agent_from_files
from app.document_set_service import run_document_set_agent_from_files


def _detect_file_types(paths: list[str | Path]) -> dict[str, Path]:
    detected: dict[str, Path] = {}

    for path in paths:
        path_obj = Path(path)
        text = read_document_text(path_obj)
        parsed = parse_trade_document(text)
        document_type = parsed["document_type"]

        if document_type not in detected:
            detected[document_type] = path_obj

    return detected


def run_document_ai_agent(paths: list[str | Path]) -> dict[str, Any]:
    """
    Main Document AI entry point.

    Routes document processing automatically:
    - 1 document: single document extraction
    - invoice + packing list: pair consistency validation
    - 3 or more documents: document set completeness validation
    """
    if not paths:
        return {
            "agent_name": "document_ai_agent",
            "status": "needs_more_information",
            "summary": "No documents were provided.",
            "plan": {},
            "report": "No documents were provided.",
            "input_resolution": {
                "source": "document_ai_router",
                "document_count": 0,
            },
            "missing_information": ["uploaded_documents"],
            "handoff_payload": {},
            "handoff_requests": [
                {
                    "target_agent": "user_agent",
                    "reason": "Ask the user to upload at least one trade or shipping document.",
                    "inputs_needed": ["uploaded_documents"],
                }
            ],
        }

    if len(paths) == 1:
        return run_document_agent_from_file(paths[0])

    detected_types = _detect_file_types(paths)

    if len(paths) == 2 and "invoice" in detected_types and "packing_list" in detected_types:
        return run_document_pair_agent_from_files(
            detected_types["invoice"],
            detected_types["packing_list"],
        )

    return run_document_set_agent_from_files(paths)
