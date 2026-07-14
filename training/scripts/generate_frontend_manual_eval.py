from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = ROOT_DIR / "training" / "data" / "frontend_manual_eval.jsonl"

SYSTEM_PROMPT = """
You are the User Agent router for a trade and logistics multi-agent system.
Return only valid JSON.
Use only these agents:
shopping_agent, document_ai_agent, logistics_agent.
Do not invent agents.
"""


def route(
    intent: str,
    agents: list[str],
    input_type: str,
    reason: str,
    missing: list[str] | None = None,
    confidence: str = "high",
) -> dict:
    return {
        "intent": intent,
        "agents_to_call": agents,
        "input_type": input_type,
        "missing_information": missing or [],
        "confidence": confidence,
        "reason": reason,
    }


def make_record(user_input: str, output: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False)},
        ],
        "expected_output": output,
    }


def main() -> None:
    examples: list[tuple[str, dict]] = [
        (
            "I need 50 TVs from India and a shipping plan.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "Find suppliers for 100 ceramic tiles, avoid China, and tell me the container needed.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "I want to buy 20 laptops and ship them to Zambia.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "Source scooters from India and give me logistics details.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "Need suppliers for solar panels, preferably not China, shipping to Finland.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "Can you find a supplier for office chairs and estimate freight?",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "I need a procurement plan for refrigerators and also tell me if FCL makes sense.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "Please get me the best supplier options for phones under 10000 USD.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "I have uploaded an invoice and packing list. Check if they match.",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "Compare my invoice with the packing list and then plan shipping.",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "I uploaded trade documents, can you validate them?",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "Check the bill of lading and certificate of origin.",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "Read these documents and extract the cargo details for logistics.",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "What container do I need for 19.4 CBM and 2250 kg?",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Should this go LCL or FCL if it is around 8 CBM?",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Give me loading advice for fragile electronics and heavy tiles.",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Can my cargo fit in a 20ft container?",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Plan shipping from India to USA for mixed fragile cargo.",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Tell me packaging requirements for non-stackable cargo.",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Can you help me?",
            route("unknown", [], "text", "The request is too vague to route safely.", missing=["clearer_user_request"], confidence="low"),
        ),
        (
            "What should I do?",
            route("unknown", [], "text", "The request is too vague to route safely.", missing=["clearer_user_request"], confidence="low"),
        ),
        (
            "Check this.",
            route("unknown", [], "text", "The request is too vague to route safely.", missing=["clearer_user_request"], confidence="low"),
        ),
        (
            "I need import help but I don't know what exactly.",
            route("unknown", [], "text", "The request is too vague to route safely.", missing=["clearer_user_request"], confidence="low"),
        ),
        (
            "Run the project.",
            route("unknown", [], "text", "The request is too vague to route safely.", missing=["clearer_user_request"], confidence="low"),
        ),
        (
            "I need 50 TVs and I also have invoice docs, what should we do?",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "I have an invoice for TVs but no packing list yet.",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "Need 12 CBM shipped to Kenya, but I don't know the container.",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Find suppliers, but I have no destination yet.",
            route(
                "unknown",
                [],
                "text",
                "The request is too vague to route safely.",
                missing=["clearer_user_request"],
                confidence="low",
            ),
        ),
        (
            "Can you validate docs and then tell me container?",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "I want to source and ship air conditioners to South Africa.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
    ]

    records = [make_record(text, output) for text, output in examples]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} frontend manual eval records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
