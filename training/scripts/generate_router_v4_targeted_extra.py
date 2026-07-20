from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = ROOT_DIR / "training" / "data" / "router_v4_targeted_extra.jsonl"

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


def record(user_input, output):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False)},
        ],
        "expected_output": output,
    }


SHOPPING_LOGISTICS = route(
    "shopping",
    ["shopping_agent", "logistics_agent"],
    "text",
    "The user is asking to source products and plan shipping.",
)

SHOPPING_ONLY = route(
    "shopping",
    ["shopping_agent"],
    "text",
    "The user is asking to source products only.",
)

SHOPPING_MISSING_ORIGIN = route(
    "shopping",
    ["shopping_agent", "logistics_agent"],
    "text",
    "The user is asking to source products and plan shipping.",
    ["origin_country"],
    "medium",
)

DOCUMENT_ONLY = route(
    "document",
    ["document_ai_agent"],
    "files",
    "The user is asking to validate or extract trade documents only.",
)

DOCUMENT_LOGISTICS = route(
    "document",
    ["document_ai_agent", "logistics_agent"],
    "files",
    "The user provided trade documents that should be validated before logistics planning.",
)

UNKNOWN_GENERAL = route(
    "unknown",
    [],
    "text",
    "The request is a general explanation, not a clear routing request.",
    ["clearer_user_request"],
    "low",
)

UNKNOWN_SCOPE = route(
    "unknown",
    [],
    "text",
    "The request asks for an unsupported specialist in the current router schema.",
    ["supported_agent_scope"],
    "low",
)


def main():
    examples = [
        # Short / messy source + ship requests.
        ("need tvs india ship zambia", SHOPPING_LOGISTICS),
        ("need phones china ship kenya", SHOPPING_LOGISTICS),
        ("tiles india to usa shipping supplier", SHOPPING_LOGISTICS),
        ("source scooters india logistics details", SHOPPING_LOGISTICS),
        ("buy TVs from India and ship to Zambia", SHOPPING_LOGISTICS),
        ("find supplier for tiles and freight estimate", SHOPPING_LOGISTICS),
        ("estimate freight and find supplier for tiles", SHOPPING_LOGISTICS),
        ("supplier plus freight for ceramic tiles", SHOPPING_LOGISTICS),
        ("source and ship ceramic tiles", SHOPPING_LOGISTICS),
        ("find supplier and calculate shipping", SHOPPING_LOGISTICS),
        ("get suppliers and logistics details", SHOPPING_LOGISTICS),
        ("supplier search with shipping plan", SHOPPING_LOGISTICS),
        ("source scooters from India and give logistics details", SHOPPING_LOGISTICS),
        ("find refrigerator suppliers and container plan", SHOPPING_LOGISTICS),
        ("need air conditioners supplier and shipping plan", SHOPPING_LOGISTICS),
        ("procure scooters from India and give freight plan", SHOPPING_LOGISTICS),
        ("find TV suppliers and tell me the shipment plan", SHOPPING_LOGISTICS),
        ("source ceramic tiles and check LCL or FCL", SHOPPING_LOGISTICS),

        # Shopping only / explicitly no logistics.
        ("source phones from china but ship later", SHOPPING_ONLY),
        ("find suppliers only, no shipping needed", SHOPPING_ONLY),
        ("get me suppliers only, I will handle logistics later", SHOPPING_ONLY),
        ("supplier shortlist only, no freight", SHOPPING_ONLY),
        ("find vendors but don't calculate shipping", SHOPPING_ONLY),

        # Missing origin / source country but still sourcing request.
        ("need to import ceramic tiles but not sure from where", SHOPPING_MISSING_ORIGIN),
        ("I want to import TVs but not sure from which country", SHOPPING_MISSING_ORIGIN),
        ("need suppliers for tiles, origin country unknown", SHOPPING_MISSING_ORIGIN),
        ("not sure where to source ceramic tiles from", SHOPPING_MISSING_ORIGIN),
        ("help me choose source country for scooters and plan shipment", SHOPPING_MISSING_ORIGIN),
        ("I know the product but not the supplier country", SHOPPING_MISSING_ORIGIN),
        ("want to import refrigerators but source country not decided", SHOPPING_MISSING_ORIGIN),
        ("need ceramic tiles, don't know where to buy from", SHOPPING_MISSING_ORIGIN),

        # Document validation only.
        ("uploaded invoice pls check", DOCUMENT_ONLY),
        ("I uploaded trade documents, can you validate them?", DOCUMENT_ONLY),
        ("I have an invoice for TVs but no packing list yet.", DOCUMENT_ONLY),
        ("please validate uploaded docs only", DOCUMENT_ONLY),
        ("check invoice only", DOCUMENT_ONLY),
        ("read my invoice and tell me if it is complete", DOCUMENT_ONLY),
        ("validate the packing list", DOCUMENT_ONLY),
        ("check document fields", DOCUMENT_ONLY),

        # Document + logistics when explicitly requested.
        ("validate documents then plan shipping", DOCUMENT_LOGISTICS),
        ("check uploaded invoice and packing list then estimate container", DOCUMENT_LOGISTICS),
        ("extract cargo details from documents and plan shipment", DOCUMENT_LOGISTICS),
        ("compare docs and give me logistics plan", DOCUMENT_LOGISTICS),

        # General / unsupported requests.
        ("what is incoterm", UNKNOWN_GENERAL),
        ("explain CIF", UNKNOWN_GENERAL),
        ("what does FOB mean", UNKNOWN_GENERAL),
        ("can you do compliance for this import?", UNKNOWN_SCOPE),
        ("calculate duties for this import", UNKNOWN_SCOPE),
        ("ask finance agent to check payment terms", UNKNOWN_SCOPE),
    ]

    records = [record(text, output) for text, output in examples]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        for item in records:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} targeted V4 examples to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
