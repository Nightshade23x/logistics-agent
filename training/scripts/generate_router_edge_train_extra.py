from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = ROOT_DIR / "training" / "data" / "router_edge_train_extra.jsonl"

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


SHOPPING_ONLY = route(
    "shopping",
    ["shopping_agent"],
    "text",
    "The user is asking to source products only.",
)

SHOPPING_LOGISTICS = route(
    "shopping",
    ["shopping_agent", "logistics_agent"],
    "text",
    "The user is asking to source products and plan shipping.",
)

LOGISTICS_ONLY = route(
    "logistics",
    ["logistics_agent"],
    "text",
    "The user is asking for shipment, container, CBM, or cargo planning.",
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

UNKNOWN_VAGUE = route(
    "unknown",
    [],
    "text",
    "The request is too vague to route safely.",
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

UNKNOWN_GENERAL = route(
    "unknown",
    [],
    "text",
    "The request is a general explanation, not a clear routing request.",
    ["clearer_user_request"],
    "low",
)

SHOPPING_MISSING_ORIGIN = route(
    "shopping",
    ["shopping_agent", "logistics_agent"],
    "text",
    "The user is asking to source products and plan shipping.",
    ["origin_country"],
    "medium",
)


def main():
    examples = [
        # Vague/context-dependent supplier requests should not be routed.
        ("find suppliers for the thing from earlier", UNKNOWN_VAGUE),
        ("get suppliers for that item", UNKNOWN_VAGUE),
        ("source what we talked about", UNKNOWN_VAGUE),
        ("find vendors for it", UNKNOWN_VAGUE),
        ("supplier search please", UNKNOWN_VAGUE),

        # Explicit shopping only / no logistics.
        ("find suppliers only, do not plan shipping", SHOPPING_ONLY),
        ("source laptops only, no freight estimate", SHOPPING_ONLY),
        ("I only need supplier options for phones", SHOPPING_ONLY),
        ("get vendors for tiles, shipping is not needed", SHOPPING_ONLY),
        ("source TVs now, I will handle shipping later", SHOPPING_ONLY),
        ("find suppliers for scooters but don't do logistics", SHOPPING_ONLY),
        ("supplier shortlist only", SHOPPING_ONLY),
        ("compare suppliers only", SHOPPING_ONLY),
        ("procurement only, no container planning", SHOPPING_ONLY),
        ("find product suppliers, not shipping", SHOPPING_ONLY),

        # Shopping + logistics mixed requests.
        ("find tile suppliers and estimate freight", SHOPPING_LOGISTICS),
        ("source ceramic tiles and calculate container needs", SHOPPING_LOGISTICS),
        ("get suppliers for TVs and plan shipment", SHOPPING_LOGISTICS),
        ("supplier search plus freight estimate for refrigerators", SHOPPING_LOGISTICS),
        ("find phone vendors and shipping options", SHOPPING_LOGISTICS),
        ("source air conditioners and tell me LCL or FCL", SHOPPING_LOGISTICS),
        ("buy office chairs and estimate container space", SHOPPING_LOGISTICS),
        ("get supplier options and freight plan", SHOPPING_LOGISTICS),
        ("find supplier and calculate CBM", SHOPPING_LOGISTICS),
        ("source products and shipping together", SHOPPING_LOGISTICS),

        # Unsupported/general requests should stay unknown for current schema.
        ("can you check compliance for this import", UNKNOWN_SCOPE),
        ("do customs compliance for these goods", UNKNOWN_SCOPE),
        ("what duties will I pay", UNKNOWN_SCOPE),
        ("calculate import tax", UNKNOWN_SCOPE),
        ("ask trader agent to negotiate", UNKNOWN_SCOPE),
        ("can finance agent check payment terms", UNKNOWN_SCOPE),
        ("risk agent please review this", UNKNOWN_SCOPE),

        # General explanations should not route to logistics.
        ("what is an incoterm", UNKNOWN_GENERAL),
        ("explain FOB", UNKNOWN_GENERAL),
        ("what does CIF mean", UNKNOWN_GENERAL),
        ("teach me about import documents", UNKNOWN_GENERAL),
        ("what is a bill of lading", UNKNOWN_GENERAL),

        # Document only vs document + logistics.
        ("only check my invoice and packing list", DOCUMENT_ONLY),
        ("validate documents only, no shipping plan", DOCUMENT_ONLY),
        ("extract document fields only", DOCUMENT_ONLY),
        ("check my trade docs but don't do logistics", DOCUMENT_ONLY),
        ("read the invoice and do not plan shipment", DOCUMENT_ONLY),
        ("validate docs then plan shipping", DOCUMENT_LOGISTICS),
        ("extract cargo from docs and estimate container", DOCUMENT_LOGISTICS),
        ("compare invoice and packing list then calculate freight", DOCUMENT_LOGISTICS),
        ("check uploaded docs and route to logistics", DOCUMENT_LOGISTICS),

        # Logistics only.
        ("container planning only", LOGISTICS_ONLY),
        ("freight estimate only, supplier already selected", LOGISTICS_ONLY),
        ("I already have supplier, plan shipment", LOGISTICS_ONLY),
        ("should I use LCL or FCL", LOGISTICS_ONLY),
        ("calculate container for 22 CBM", LOGISTICS_ONLY),

        # Missing origin but still import/source request.
        ("I need to import tiles but I don't know the source country", SHOPPING_MISSING_ORIGIN),
        ("source ceramic tiles, origin not decided yet", SHOPPING_MISSING_ORIGIN),
        ("I need TVs but not sure where to buy from", SHOPPING_MISSING_ORIGIN),
        ("help me import refrigerators, supplier country unknown", SHOPPING_MISSING_ORIGIN),
        ("find the best country to source scooters from", SHOPPING_MISSING_ORIGIN),
    ]

    records = [record(text, output) for text, output in examples]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        for item in records:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} hard training examples to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
