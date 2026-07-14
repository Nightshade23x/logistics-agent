from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


VALID_INTENTS = {"shopping", "document", "logistics", "unknown"}
VALID_AGENTS = {"shopping_agent", "document_ai_agent", "logistics_agent"}
VALID_CONFIDENCE = {"low", "medium", "high"}

DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_ADAPTER_PATH = "G:/ai-models/checkpoints/router-qwen-0.5b-lora-150/final_adapter"
DEFAULT_EVAL_FILE = "training/data/eval.jsonl"
DEFAULT_OUTPUT_FILE = "training/outputs/router_eval_predictions.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            records.append(json.loads(line))

    return records


def save_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

def validate_router_output(output: dict[str, Any]) -> list[str]:
    errors = []

    if output.get("intent") not in VALID_INTENTS:
        errors.append(f"invalid_intent:{output.get('intent')}")

    agents = output.get("agents_to_call")
    if not isinstance(agents, list):
        errors.append("agents_to_call_not_list")
    else:
        for agent in agents:
            if agent not in VALID_AGENTS:
                errors.append(f"invalid_agent:{agent}")

    if not isinstance(output.get("input_type"), str):
        errors.append("input_type_missing_or_invalid")

    if not isinstance(output.get("missing_information", []), list):
        errors.append("missing_information_not_list")

    if output.get("confidence") not in VALID_CONFIDENCE:
        errors.append(f"invalid_confidence:{output.get('confidence')}")

    if not isinstance(output.get("reason"), str):
        errors.append("reason_missing_or_invalid")

    return errors


def compare_outputs(predicted: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    return {
        "intent_correct": predicted.get("intent") == expected.get("intent"),
        "agents_correct": predicted.get("agents_to_call") == expected.get("agents_to_call"),
        "input_type_correct": predicted.get("input_type") == expected.get("input_type"),
        "missing_info_correct": predicted.get("missing_information") == expected.get("missing_information"),
    }


def is_full_match(comparison: dict[str, bool]) -> bool:
    return all(comparison.values())

def build_prompt(tokenizer, messages: list[dict[str, str]]) -> str:
    return tokenizer.apply_chat_template(
        messages[:-1],
        tokenize=False,
        add_generation_prompt=True,
    )


def load_model(base_model_name: str, adapter_path):
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    if adapter_path is None:
        tokenizer = AutoTokenizer.from_pretrained(
            base_model_name,
            trust_remote_code=True,
        )

        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            dtype=dtype,
            trust_remote_code=True,
        )
    else:
        tokenizer = AutoTokenizer.from_pretrained(
            adapter_path,
            trust_remote_code=True,
        )

        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            dtype=dtype,
            trust_remote_code=True,
        )

        model = PeftModel.from_pretrained(
            base_model,
            adapter_path,
        )

    if torch.cuda.is_available():
        model = model.to("cuda")

    model.eval()
    return model, tokenizer

def generate_prediction(model, tokenizer, messages: list[dict[str, str]], max_new_tokens: int) -> str:
    prompt = build_prompt(tokenizer, messages)

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    )

    if torch.cuda.is_available():
        inputs = {key: value.to("cuda") for key, value in inputs.items()}

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--adapter-path", default=DEFAULT_ADAPTER_PATH)
    parser.add_argument("--eval-file", default=DEFAULT_EVAL_FILE)
    parser.add_argument("--output-file", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--max-new-tokens", type=int, default=180)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    adapter_path = None if args.adapter_path.lower() in {"none", "base", "no-adapter"} else Path(args.adapter_path)
    eval_file = Path(args.eval_file)
    output_file = Path(args.output_file)

    records = load_jsonl(eval_file)
    if args.limit > 0:
        records = records[: args.limit]

    print("TRAINED ROUTER EVALUATION")
    print("=" * 40)
    print(f"Base model: {args.base_model}")
    print(f"Adapter: {adapter_path}")
    print(f"Eval file: {eval_file}")
    print(f"Records: {len(records)}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'}")
    print("")

    model, tokenizer = load_model(args.base_model, adapter_path)

    results = []
    json_valid = 0
    schema_valid = 0
    intent_correct = 0
    agents_correct = 0
    input_type_correct = 0
    missing_info_correct = 0
    full_match = 0

    for index, record in enumerate(records, start=1):
        expected = record["expected_output"]
        raw_prediction = generate_prediction(
            model=model,
            tokenizer=tokenizer,
            messages=record["messages"],
            max_new_tokens=args.max_new_tokens,
        )

        parsed_prediction = None
        parse_error = None
        schema_errors = []
        comparison = {
            "intent_correct": False,
            "agents_correct": False,
            "input_type_correct": False,
            "missing_info_correct": False,
        }

        try:
            parsed_prediction = json.loads(raw_prediction)
            json_valid += 1
            schema_errors = validate_router_output(parsed_prediction)

            if not schema_errors:
                schema_valid += 1
                comparison = compare_outputs(parsed_prediction, expected)

                intent_correct += int(comparison["intent_correct"])
                agents_correct += int(comparison["agents_correct"])
                input_type_correct += int(comparison["input_type_correct"])
                missing_info_correct += int(comparison["missing_info_correct"])
                full_match += int(is_full_match(comparison))

        except json.JSONDecodeError as error:
            parse_error = str(error)

        results.append(
            {
                "index": index,
                "user_input": record["messages"][1]["content"],
                "expected": expected,
                "raw_prediction": raw_prediction,
                "parsed_prediction": parsed_prediction,
                "parse_error": parse_error,
                "schema_errors": schema_errors,
                "comparison": comparison,
            }
        )

    total = len(records)

    print("RESULTS")
    print("=" * 40)
    print(f"JSON valid: {json_valid}/{total}")
    print(f"Schema valid: {schema_valid}/{total}")
    print(f"Intent accuracy: {intent_correct}/{total}")
    print(f"Agent-chain accuracy: {agents_correct}/{total}")
    print(f"Input-type accuracy: {input_type_correct}/{total}")
    print(f"Missing-info accuracy: {missing_info_correct}/{total}")
    print(f"Full routing accuracy: {full_match}/{total}")
    print("")
    print(f"Saved predictions to: {output_file}")

    save_jsonl(output_file, results)


if __name__ == "__main__":
    main()
