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

RNG = random.Random(42)


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


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

def shopping_examples() -> list[dict]:
    products = [
        "TVs",
        "scooters",
        "ceramic tiles",
        "laptops",
        "phones",
        "washing machines",
        "solar panels",
        "LED lights",
        "office chairs",
        "air conditioners",
        "refrigerators",
        "water pumps",
    ]

    countries = [
        "India",
        "Vietnam",
        "China",
        "Turkey",
        "Germany",
        "Malaysia",
        "Thailand",
    ]

    destination_countries = [
        "USA",
        "Zambia",
        "Finland",
        "UAE",
        "South Africa",
        "Kenya",
    ]

    templates = [
        "I need {qty1} {p1}, {qty2} {p2}, and {qty3} {p3}. Prefer suppliers from {country}. Avoid {avoid}. Budget {budget} USD.",
        "Find suppliers for {qty1} {p1} and {qty2} {p2}, then estimate the shipment to {dest}.",
        "Source {p1} from {country} and tell me what container I may need.",
        "I want to buy {qty1} {p1} and {qty2} {p2}. Please also plan logistics.",
        "Find reliable suppliers for {p1}, compare options, and prepare a freight plan.",
        "I need a procurement and shipping plan for {p1}, {p2}, and {p3}.",
        "Can you source {qty1} {p1} under {budget} USD and check shipping requirements?",
        "For an import order, find {p1} suppliers in {country} and estimate the container.",
        "Purchase {p1} and {p2}; avoid suppliers from {avoid}; then plan shipment.",
        "I need suppliers and logistics for {qty1} {p1} going to {dest}.",
    ]

    records = []

    for _ in range(130):
        p1, p2, p3 = RNG.sample(products, 3)
        country = RNG.choice(countries)
        avoid = RNG.choice([c for c in countries if c != country])
        dest = RNG.choice(destination_countries)
        qty1 = RNG.choice([5, 10, 20, 50, 100, 200, 500])
        qty2 = RNG.choice([3, 5, 10, 25, 75, 150])
        qty3 = RNG.choice([10, 50, 100, 250, 1000])
        budget = RNG.choice([5000, 10000, 13000, 20000, 50000, 75000])
        text = RNG.choice(templates).format(
            p1=p1,
            p2=p2,
            p3=p3,
            country=country,
            avoid=avoid,
            dest=dest,
            qty1=qty1,
            qty2=qty2,
            qty3=qty3,
            budget=budget,
        )

        records.append(
            make_record(
                text,
                route(
                    intent="shopping",
                    agents=["shopping_agent", "logistics_agent"],
                    input_type="text",
                    reason="The user is asking to source products and plan shipping.",
                ),
            )
        )

    return records

def document_examples() -> list[dict]:
    document_sets = [
        "invoice and packing list",
        "invoice, packing list, and bill of lading",
        "packing list and certificate of origin",
        "trade documents",
        "bill of lading and invoice",
        "commercial invoice and packing list",
    ]

    actions = [
        "check if they match",
        "validate them",
        "compare the quantities and weights",
        "check for mismatches",
        "extract the cargo details",
        "review the documents",
    ]

    templates = [
        "I uploaded an {docs}. Please {action} and create a shipping plan.",
        "Use these {docs}, {action}, then route the cargo to logistics.",
        "Can you read the {docs}, {action}, and calculate the container needed?",
        "Please process my {docs}. After validation, prepare a logistics plan.",
        "Check the {docs} and tell me if the shipment details are consistent.",
        "Here are the {docs}. Validate them before planning freight.",
        "Review my {docs}; if everything matches, estimate CBM and container.",
        "I have uploaded {docs}. {action} and prepare the shipment plan.",
    ]

    records = []

    for _ in range(85):
        docs = RNG.choice(document_sets)
        action = RNG.choice(actions)
        text = RNG.choice(templates).format(docs=docs, action=action)

        records.append(
            make_record(
                text,
                route(
                    intent="document",
                    agents=["document_ai_agent", "logistics_agent"],
                    input_type="files",
                    reason="The user provided trade documents that should be validated before logistics planning.",
                ),
            )
        )

    return records

def logistics_examples() -> list[dict]:
    origins = ["India", "China", "Vietnam", "Turkey", "Germany", "Malaysia"]
    destinations = ["USA", "Zambia", "Finland", "UAE", "South Africa", "Kenya"]
    cargo_types = [
        "fragile cargo",
        "heavy cargo",
        "non-stackable cargo",
        "electronics",
        "ceramic tiles",
        "scooters",
        "mixed cargo",
        "machinery parts",
    ]

    templates = [
        "What container do I need for {cbm} CBM and {weight} kg?",
        "Calculate whether LCL or FCL is better for {cbm} CBM.",
        "Plan a shipment from {origin} to {dest} with {cargo}.",
        "Give me loading advice for {cargo}.",
        "Check if my cargo fits in a 20ft container: {cbm} CBM and {weight} kg.",
        "I need a container recommendation and loading sequence for {cargo}.",
        "Estimate shipping load type for {cbm} CBM cargo going from {origin} to {dest}.",
        "My cargo is {weight} kg and {cbm} CBM. Should I use 20ft or 40ft?",
        "Create a logistics plan for {cargo} with total weight {weight} kg.",
        "Tell me packaging and securing requirements for {cargo}.",
    ]

    records = []

    for _ in range(110):
        text = RNG.choice(templates).format(
            cbm=RNG.choice([3, 8, 12, 19, 28, 35, 55, 70]),
            weight=RNG.choice([500, 1200, 2250, 5000, 12000, 24000]),
            origin=RNG.choice(origins),
            dest=RNG.choice(destinations),
            cargo=RNG.choice(cargo_types),
        )

        records.append(
            make_record(
                text,
                route(
                    intent="logistics",
                    agents=["logistics_agent"],
                    input_type="text",
                    reason="The user is asking for shipment, container, CBM, or cargo planning.",
                ),
            )
        )

    return records

def unknown_examples() -> list[dict]:
    texts = [
        "Can you help me?",
        "I want a plan.",
        "Tell me the cost.",
        "Check this for me.",
        "I need import help.",
        "What should I do next?",
        "Please handle this.",
        "Is this okay?",
        "Give me the answer.",
        "Can we start?",
        "What is the best option?",
        "Help with the project.",
        "I have some products.",
        "I need something shipped.",
        "Can you review it?",
    ]

    records = []

    for text in texts * 4:
        records.append(
            make_record(
                text,
                route(
                    intent="unknown",
                    agents=[],
                    input_type="text",
                    reason="The request is too vague to route safely.",
                    missing=["clearer_user_request"],
                    confidence="low",
                ),
            )
        )

    return records


def json_examples() -> list[dict]:
    shopping_jsons = [
        '{"items":[{"name":"TVs","quantity":50}],"destination_country":"USA"}',
        '{"customer":"Demo","destination_country":"Zambia","items":[{"name":"solar panels","quantity":100}]}',
        '{"request_id":"SHOP-001","items":[{"name":"laptops","quantity":20}],"preferences":{"preferred_supplier_countries":["India"]}}',
        '{"items":[{"name":"ceramic tiles","quantity":500}],"destination_country":"Finland","budget_usd":10000}',
    ]

    logistics_jsons = [
        '{"origin":"India","destination":"USA","items":[{"name":"TVs","quantity":10,"length_cm":120,"width_cm":20,"height_cm":75,"weight_kg":12}]}',
        '{"shipment_id":"LOG-001","origin":"Vietnam","destination":"Zambia","items":[{"name":"scooters","quantity":5,"length_cm":180,"width_cm":70,"height_cm":110,"weight_kg":90}]}',
        '{"origin":"China","destination":"UAE","items":[{"name":"machinery","quantity":2,"total_cbm":12,"weight_kg":3000}]}',
        '{"origin":"Turkey","destination":"Kenya","items":[{"name":"tiles","quantity":100,"length_cm":60,"width_cm":60,"height_cm":8,"weight_kg":12}]}',
    ]

    records = []

    for text in shopping_jsons * 5:
        records.append(
            make_record(
                text,
                route(
                    intent="shopping",
                    agents=["shopping_agent", "logistics_agent"],
                    input_type="json",
                    reason="The JSON contains a procurement request.",
                ),
            )
        )

    for text in logistics_jsons * 5:
        records.append(
            make_record(
                text,
                route(
                    intent="logistics",
                    agents=["logistics_agent"],
                    input_type="json",
                    reason="The JSON contains origin, destination, cargo dimensions, and weight.",
                ),
            )
        )

    return records

def challenge_examples() -> list[dict]:
    examples = [
        (
            "Need 40 refrigerators from Vietnam, shipping to Zambia. Budget is 22k. Need supplier and freight plan.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "I only know my cargo is 16 CBM and 1800kg. Should I use LCL or FCL?",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "I have uploaded the commercial invoice and packing list. Please compare them before planning delivery.",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "Can you check my import thing?",
            route("unknown", [], "text", "The request is too vague to route safely.", missing=["clearer_user_request"], confidence="low"),
        ),
        (
            "Source office chairs, avoid China, prefer Turkey, and tell me container requirements.",
            route("shopping", ["shopping_agent", "logistics_agent"], "text", "The user is asking to source products and plan shipping."),
        ),
        (
            "The cargo is fragile electronics, 9.5 CBM, 700 kg. Give packaging and loading advice.",
            route("logistics", ["logistics_agent"], "text", "The user is asking for shipment, container, CBM, or cargo planning."),
        ),
        (
            "Please validate the bill of lading and invoice and then estimate cargo movement.",
            route("document", ["document_ai_agent", "logistics_agent"], "files", "The user provided trade documents that should be validated before logistics planning."),
        ),
        (
            "What now?",
            route("unknown", [], "text", "The request is too vague to route safely.", missing=["clearer_user_request"], confidence="low"),
        ),
    ]

    return [make_record(text, output) for text, output in examples]


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    records.extend(shopping_examples())
    records.extend(document_examples())
    records.extend(logistics_examples())
    records.extend(unknown_examples())
    records.extend(json_examples())

    RNG.shuffle(records)

    split = int(len(records) * 0.8)
    train_records = records[:split]
    eval_records = records[split:]
    challenge_records = challenge_examples()

    write_jsonl(DATA_DIR / "train.jsonl", train_records)
    write_jsonl(DATA_DIR / "eval.jsonl", eval_records)
    write_jsonl(DATA_DIR / "challenge_eval.jsonl", challenge_records)

    print(f"Wrote {len(train_records)} training records.")
    print(f"Wrote {len(eval_records)} eval records.")
    print(f"Wrote {len(challenge_records)} challenge eval records.")


if __name__ == "__main__":
    main()
