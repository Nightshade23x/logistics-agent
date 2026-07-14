from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = ROOT_DIR / "training" / "data" / "router_edge_eval.jsonl"

SYSTEM_PROMPT = """
You are the User Agent router for a trade and logistics multi-agent system.
Return only valid JSON.
Use only these agents:
shopping_agent, document_ai_agent, logistics_agent.
Do not invent agents.
"""


def route(intent, agents, input_type, reason, missing=None, confidence="high"):
    return {
        "intent": intent,
        "agents_to_call": agents,
        "input_type": input_type,
        "missing_information": missing or [],
        "confidence": confidence,
        "reason": reason,
    }


def make_record(user_input, output):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False)},
        ],
        "expected_output": output,
    }


def main():
    examples = [
        (
            "need tvs india ship zambia",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "find suppliers for what we discussed",
            route("unknown", [], "text", "The request is too vague to route safely.", ["clearer_user_request"], "low"),
        ),
        (
            "i have 15 cbm and 3 tons. container?",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "uploaded invoice pls check",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "get me suppliers only, no shipping needed",
            route("shopping", ["shopping_agent"], "text", "The user is asking to source products."),
        ),
        (
            "shipping only, supplier already chosen",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "can you do compliance for this import?",
            route("unknown", [], "text", "The request asks for an unsupported specialist in the current router schema.", ["supported_agent_scope"], "low"),
        ),
        (
            "estimate freight and find supplier for tiles",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "compare invoice packing list and tell me if cargo fits 20ft",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "I need help with logistics but no cargo details yet",
            route("unknown", [], "text", "The request is too vague to route safely.", ["clearer_user_request"], "low"),
        ),
        (
            "source phones from china but ship later",
            route("shopping", ["shopping_agent"], "text", "The user is asking to source products."),
        ),
        (
            "source phones from china and estimate shipping later",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "docs are uploaded, extract item weights dimensions and route",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "what is incoterm",
            route("unknown", [], "text", "The request is a general explanation, not a clear routing request.", ["clearer_user_request"], "low"),
        ),
        (
            "40 refrigerators, india to kenya, cheapest supplier and container",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "only check my documents, dont plan shipping",
            route("document", ["document_ai_agent"], "files", "The user is asking to validate or extract trade documents only."),
        ),
        (
            "only container planning, no supplier search",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "buy stuff",
            route("unknown", [], "text", "The request is too vague to route safely.", ["clearer_user_request"], "low"),
        ),
        (
            "need to import ceramic tiles but not sure from where",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping.", ["origin_country"], "medium"),
        ),
        (
            "I have supplier and docs, check docs then shipping",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
    ]

    records = [make_record(text, output) for text, output in examples]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} edge eval records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
