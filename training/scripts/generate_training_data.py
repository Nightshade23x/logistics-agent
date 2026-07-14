from __future__ import annotations

import json
import random
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "training" / "data"

SYSTEM_PROMPT = """
You are the User Agent router for a trade and logistics multi-agent system.
Return only valid JSON.
Use only these agents:
shopping_agent, document_ai_agent, logistics_agent.
Do not invent agents.
"""


def make_record(user_input: str, output: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": json.dumps(output)},
        ],
        "expected_output": output,
    }


def route(intent: str, agents: list[str], input_type: str, reason: str, missing=None, confidence="high") -> dict:
    return {
        "intent": intent,
        "agents_to_call": agents,
        "input_type": input_type,
        "missing_information": missing or [],
        "confidence": confidence,
        "reason": reason,
    }


def build_examples() -> list[dict]:
    records = []

    shopping_texts = [
        "I need 50 TVs, 5 scooters, and 100 ceramic tiles from India. Avoid China. Budget 13000 USD.",
        "Find suppliers for laptops and estimate shipping.",
        "Source ceramic tiles and tell me what container I need.",
        "I want to buy electronics and plan the shipment.",
        "Find scooter suppliers and calculate logistics.",
        "Purchase building materials and prepare a freight plan.",
    ]

    for text in shopping_texts:
        records.append(make_record(text, route(
            "shopping",
            ["shopping_agent", "logistics_agent"],
            "text",
            "The user is asking to source products and plan shipping."
        )))

    document_texts = [
        "I have an invoice and packing list. Check if they match and create a shipping plan.",
        "Validate these trade documents and calculate the container needed.",
        "Compare invoice and packing list, then plan logistics.",
        "Review the bill of lading and packing list.",
        "I uploaded trade documents. Check them and route cargo to logistics.",
    ]

    for text in document_texts:
        records.append(make_record(text, route(
            "document",
            ["document_ai_agent", "logistics_agent"],
            "files",
            "The user provided trade documents that should be validated before logistics planning."
        )))

    logistics_texts = [
        "What container do I need for 19 CBM and 2250 kg?",
        "Calculate CBM and tell me whether LCL or FCL is better.",
        "Plan a shipment from India to USA with cargo dimensions.",
        "Give me loading advice for fragile and heavy cargo.",
        "Check if my cargo fits in a 20ft container.",
    ]

    for text in logistics_texts:
        records.append(make_record(text, route(
            "logistics",
            ["logistics_agent"],
            "text",
            "The user is asking for shipment, container, CBM, or cargo planning."
        )))

    unknown_texts = [
        "Can you help me?",
        "I want a plan.",
        "Tell me the cost.",
        "Check this for me.",
        "I need import help.",
    ]

    for text in unknown_texts:
        records.append(make_record(text, route(
            "unknown",
            [],
            "text",
            "The request is too vague to route safely.",
            missing=["clearer_user_request"],
            confidence="low"
        )))

    records.append(make_record(
        '{"items":[{"name":"TVs","quantity":50}],"destination_country":"USA"}',
        route(
            "shopping",
            ["shopping_agent", "logistics_agent"],
            "json",
            "The JSON contains a procurement request."
        )
    ))

    records.append(make_record(
        '{"origin":"India","destination":"USA","items":[{"name":"TVs","quantity":10,"length_cm":120,"width_cm":20,"height_cm":75,"weight_kg":12}]}',
        route(
            "logistics",
            ["logistics_agent"],
            "json",
            "The JSON contains origin, destination, cargo dimensions, and weight."
        )
    ))

    return records


def expand_examples(records: list[dict]) -> list[dict]:
    prefixes = ["", "Please help: ", "For an import project, ", "Urgent: "]
    expanded = []

    for record in records:
        user_text = record["messages"][1]["content"]
        output = record["expected_output"]

        for prefix in prefixes:
            expanded.append(make_record(prefix + user_text, dict(output)))

    random.Random(42).shuffle(expanded)
    return expanded


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = expand_examples(build_examples())
    split = int(len(records) * 0.8)

    train = records[:split]
    eval_set = records[split:]

    write_jsonl(DATA_DIR / "train.jsonl", train)
    write_jsonl(DATA_DIR / "eval.jsonl", eval_set)

    print(f"Wrote {len(train)} training records.")
    print(f"Wrote {len(eval_set)} eval records.")


if __name__ == "__main__":
    main()
