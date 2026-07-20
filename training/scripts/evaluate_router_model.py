from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


VALID_INTENTS = {"shopping", "document", "logistics", "unknown"}
VALID_AGENTS = {"shopping_agent", "document_ai_agent", "logistics_agent"}
VALID_CONFIDENCE = {"low", "medium", "high"}


def validate_output(output: dict) -> list[str]:
    errors = []

    if output.get("intent") not in VALID_INTENTS:
        errors.append(f"Invalid intent: {output.get('intent')}")

    agents = output.get("agents_to_call")
    if not isinstance(agents, list):
        errors.append("agents_to_call must be a list")
    else:
        for agent in agents:
            if agent not in VALID_AGENTS:
                errors.append(f"Invalid agent: {agent}")

    if not isinstance(output.get("missing_information", []), list):
        errors.append("missing_information must be a list")

    if output.get("confidence") not in VALID_CONFIDENCE:
        errors.append(f"Invalid confidence: {output.get('confidence')}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()

    path = Path(args.dataset)
    total = 0
    invalid = 0
    intent_counts = Counter()
    agent_counts = Counter()

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            total += 1
            record = json.loads(line)
            output = record["expected_output"]

            errors = validate_output(output)
            if errors:
                invalid += 1
                print(f"Line {line_number}: {errors}")

            intent_counts[output["intent"]] += 1

            for agent in output["agents_to_call"]:
                agent_counts[agent] += 1

    print("DATASET VALIDATION")
    print("=" * 30)
    print(f"Dataset: {path}")
    print(f"Total records: {total}")
    print(f"Invalid records: {invalid}")

    print("")
    print("Intent counts:")
    for intent, count in intent_counts.items():
        print(f"- {intent}: {count}")

    print("")
    print("Agent counts:")
    for agent, count in agent_counts.items():
        print(f"- {agent}: {count}")


if __name__ == "__main__":
    main()
