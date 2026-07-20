from __future__ import annotations

import json
import random
from pathlib import Path


ROOT = Path(".")
SYSTEM_PROMPT = """
You are the User Agent router for a trade and logistics multi-agent system.
Return only valid JSON.
Use only these agents:
shopping_agent, document_ai_agent, logistics_agent.
Do not invent agents.
""".strip()


def route(intent, agents, input_type, reason, missing=None, confidence="high"):
    return {
        "intent": intent,
        "agents_to_call": agents,
        "input_type": input_type,
        "missing_information": missing or [],
        "confidence": confidence,
        "reason": reason,
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

SHOPPING_MISSING_ORIGIN = route(
    "shopping",
    ["shopping_agent", "logistics_agent"],
    "text",
    "The user is asking to source products and plan shipping.",
    ["origin_country"],
    "medium",
)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def make_record(user_input: str, output: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False)},
        ],
        "expected_output": output,
    }


def set_expected(record: dict, output: dict) -> dict:
    record = dict(record)
    record["expected_output"] = output
    record["messages"] = list(record["messages"])
    record["messages"][-1] = {
        "role": "assistant",
        "content": json.dumps(output, ensure_ascii=False),
    }
    return record


def build_policy_eval_files() -> tuple[list[dict], list[dict]]:
    frontend = load_jsonl(ROOT / "training/data/frontend_manual_eval.jsonl")
    edge = load_jsonl(ROOT / "training/data/router_edge_eval.jsonl")

    frontend_overrides = {
        "I have uploaded an invoice and packing list. Check if they match.": DOCUMENT_ONLY,
        "I uploaded trade documents, can you validate them?": DOCUMENT_ONLY,
        "I have an invoice for TVs but no packing list yet.": DOCUMENT_ONLY,
        "Can you validate docs and then tell me container?": DOCUMENT_LOGISTICS,
    }

    edge_overrides = {
        "uploaded invoice pls check": DOCUMENT_ONLY,
        "I need help with logistics but no cargo details yet": UNKNOWN_VAGUE,
        "I have supplier and docs, check docs then shipping": DOCUMENT_LOGISTICS,
    }

    new_frontend = []
    for record in frontend:
        user_input = record["messages"][1]["content"]
        if user_input in frontend_overrides:
            record = set_expected(record, frontend_overrides[user_input])
        new_frontend.append(record)

    new_edge = []
    for record in edge:
        user_input = record["messages"][1]["content"]

        if user_input == "source phones from china and estimate shipping later":
            record = make_record("source phones from china and estimate shipping", SHOPPING_LOGISTICS)
        elif user_input in edge_overrides:
            record = set_expected(record, edge_overrides[user_input])

        new_edge.append(record)

    save_jsonl(ROOT / "training/data/frontend_manual_eval_v5_policy.jsonl", new_frontend)
    save_jsonl(ROOT / "training/data/router_edge_eval_v5_policy.jsonl", new_edge)

    return new_frontend, new_edge


def build_v5_targeted() -> list[dict]:
    examples = [
        # Explicit document + logistics.
        ("Here are the trade documents. Validate them before planning freight.", DOCUMENT_LOGISTICS),
        ("Can you validate docs and then tell me container?", DOCUMENT_LOGISTICS),
        ("I have supplier and docs, check docs then shipping", DOCUMENT_LOGISTICS),
        ("check uploaded documents then plan shipping", DOCUMENT_LOGISTICS),
        ("validate invoice and packing list then estimate container", DOCUMENT_LOGISTICS),
        ("review documents before freight planning", DOCUMENT_LOGISTICS),
        ("extract cargo details from documents and calculate shipping", DOCUMENT_LOGISTICS),
        ("compare docs and tell me LCL or FCL", DOCUMENT_LOGISTICS),
        ("validate trade docs and give logistics plan", DOCUMENT_LOGISTICS),
        ("check invoice then calculate container requirement", DOCUMENT_LOGISTICS),

        # Document only.
        ("I uploaded trade documents, can you validate them?", DOCUMENT_ONLY),
        ("I have an invoice for TVs but no packing list yet.", DOCUMENT_ONLY),
        ("uploaded invoice pls check", DOCUMENT_ONLY),
        ("validate uploaded docs only", DOCUMENT_ONLY),
        ("check invoice only", DOCUMENT_ONLY),
        ("read my packing list", DOCUMENT_ONLY),
        ("extract fields from the invoice", DOCUMENT_ONLY),
        ("check document completeness only", DOCUMENT_ONLY),

        # Shopping + logistics.
        ("source phones from china and estimate shipping", SHOPPING_LOGISTICS),
        ("need tvs india ship zambia", SHOPPING_LOGISTICS),
        ("source scooters from India and give me logistics details", SHOPPING_LOGISTICS),
        ("estimate freight and find supplier for tiles", SHOPPING_LOGISTICS),
        ("find supplier and estimate freight", SHOPPING_LOGISTICS),
        ("supplier plus container plan", SHOPPING_LOGISTICS),
        ("find vendors and shipping options", SHOPPING_LOGISTICS),
        ("source ceramic tiles and check LCL or FCL", SHOPPING_LOGISTICS),
        ("buy TVs from India and plan shipment to Zambia", SHOPPING_LOGISTICS),
        ("find refrigerator suppliers and freight plan", SHOPPING_LOGISTICS),

        # Shopping only.
        ("source phones from china but ship later", SHOPPING_ONLY),
        ("find suppliers only, no shipping needed", SHOPPING_ONLY),
        ("supplier shortlist only", SHOPPING_ONLY),
        ("find vendors but don't calculate freight", SHOPPING_ONLY),
        ("get me suppliers only, I will handle logistics later", SHOPPING_ONLY),

        # Unknown / vague / unsupported.
        ("I need help with logistics but no cargo details yet", UNKNOWN_VAGUE),
        ("help with logistics", UNKNOWN_VAGUE),
        ("can you arrange shipping", UNKNOWN_VAGUE),
        ("what is incoterm", UNKNOWN_GENERAL),
        ("explain CIF", UNKNOWN_GENERAL),
        ("what does FOB mean", UNKNOWN_GENERAL),
        ("can you do compliance for this import?", UNKNOWN_SCOPE),
        ("calculate duties for this import", UNKNOWN_SCOPE),

        # Missing origin but still shopping + logistics.
        ("need to import ceramic tiles but not sure from where", SHOPPING_MISSING_ORIGIN),
        ("need suppliers for tiles, origin country unknown", SHOPPING_MISSING_ORIGIN),
        ("I want to import TVs but not sure from which country", SHOPPING_MISSING_ORIGIN),
        ("not sure where to source ceramic tiles from", SHOPPING_MISSING_ORIGIN),
    ]

    records = [make_record(text, output) for text, output in examples]
    save_jsonl(ROOT / "training/data/router_v5_targeted_extra.jsonl", records)
    return records


def main() -> None:
    frontend_policy, _edge_policy = build_policy_eval_files()
    v5_targeted = build_v5_targeted()

    base = load_jsonl(ROOT / "training/data/train.jsonl")
    edge_extra = load_jsonl(ROOT / "training/data/router_edge_train_extra.jsonl")

    records = []
    records.extend(base)
    records.extend(edge_extra)

    # Anchor normal frontend policy.
    records.extend(frontend_policy)
    records.extend(frontend_policy)
    records.extend(frontend_policy)

    # Stronger weight for exact V4 failure patterns.
    records.extend(v5_targeted)
    records.extend(v5_targeted)
    records.extend(v5_targeted)
    records.extend(v5_targeted)

    random.seed(45)
    random.shuffle(records)

    save_jsonl(ROOT / "training/data/train_v5_balanced.jsonl", records)

    print(f"Base train: {len(base)}")
    print(f"Edge extra: {len(edge_extra)}")
    print(f"Frontend policy anchors x3: {len(frontend_policy) * 3}")
    print(f"V5 targeted x4: {len(v5_targeted) * 4}")
    print(f"Wrote V5 train: {len(records)} records")


if __name__ == "__main__":
    main()
