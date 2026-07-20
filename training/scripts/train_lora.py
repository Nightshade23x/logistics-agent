from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_OUTPUT_DIR = "G:/ai-models/checkpoints/router-qwen-0.5b-lora"


def format_messages(messages: list[dict], tokenizer) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )

    parts = []
    for message in messages:
        parts.append(f"{message['role'].upper()}: {message['content']}")
    return "\n".join(parts)


def load_jsonl_as_dataset(path: Path):
    return load_dataset("json", data_files=str(path), split="train")


def tokenize_dataset(dataset, tokenizer, max_length: int):
    def convert_record(record):
        text = format_messages(record["messages"], tokenizer)
        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding=False,
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    return dataset.map(
        convert_record,
        remove_columns=dataset.column_names,
    )

def build_model(model_name: str):
    print(f"Loading base model: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=dtype,
    )

    model.config.pad_token_id = tokenizer.pad_token_id

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument(
        "--train-file",
        default=str(ROOT_DIR / "training" / "data" / "train.jsonl"),
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    args = parser.parse_args()

    print("TRAINING CONFIG")
    print("=" * 40)
    print(f"Model: {args.model_name}")
    print(f"Train file: {args.train_file}")
    print(f"Output dir: {args.output_dir}")
    print(f"Max steps: {args.max_steps}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'}")
    print(f"HF_HOME: {os.environ.get('HF_HOME')}")
    print("")

    train_path = Path(args.train_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model, tokenizer = build_model(args.model_name)

    raw_train = load_jsonl_as_dataset(train_path)
    train_dataset = tokenize_dataset(raw_train, tokenizer, args.max_length)

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        max_steps=args.max_steps,
        logging_steps=1,
        save_steps=args.max_steps,
        save_total_limit=1,
        report_to=[],
        fp16=torch.cuda.is_available(),
        bf16=False,
        dataloader_num_workers=0,
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )

    trainer.train()

    final_dir = output_dir / "final_adapter"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    print("")
    print("Training complete.")
    print(f"Saved LoRA adapter to: {final_dir}")


if __name__ == "__main__":
    main()
