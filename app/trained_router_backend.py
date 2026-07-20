from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.router_decision_schema import validate_router_decision


DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_ADAPTER_PATH = "G:/ai-models/checkpoints/router-qwen-0.5b-lora-v5-balanced-450/final_adapter"

SYSTEM_PROMPT = """
You are the User Agent router for a trade and logistics multi-agent system.
Return only valid JSON.
Use only these agents:
shopping_agent, document_ai_agent, logistics_agent.
Do not invent agents.
"""

_MODEL_CACHE: dict[str, Any] = {}

def _load_model(base_model_name: str, adapter_path: str):
    cache_key = f"{base_model_name}|{adapter_path}"

    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    adapter = Path(adapter_path)
    if not adapter.exists():
        raise FileNotFoundError(f"Router adapter not found: {adapter}")

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(
        adapter,
        trust_remote_code=True,
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        local_files_only=True,
        dtype=dtype,
        trust_remote_code=True,
    )

    model = PeftModel.from_pretrained(
        base_model,
        adapter,
    )

    if torch.cuda.is_available():
        model = model.to("cuda")

    model.eval()

    _MODEL_CACHE[cache_key] = (model, tokenizer, torch)
    return _MODEL_CACHE[cache_key]

def _build_prompt(tokenizer, user_text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_text},
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def predict_trained_route(
    user_text: str,
    base_model_name: str | None = None,
    adapter_path: str | None = None,
    max_new_tokens: int = 180,
) -> dict[str, Any]:
    base_model_name = base_model_name or os.environ.get("ROUTER_BASE_MODEL", DEFAULT_BASE_MODEL)
    adapter_path = adapter_path or os.environ.get("ROUTER_ADAPTER_PATH", DEFAULT_ADAPTER_PATH)

    model, tokenizer, torch = _load_model(base_model_name, adapter_path)

    prompt = _build_prompt(tokenizer, user_text)
    inputs = tokenizer(prompt, return_tensors="pt")

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
    raw_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    decision = json.loads(raw_text)
    errors = validate_router_decision(decision)

    if errors:
        raise ValueError(f"Invalid router decision: {errors}. Raw output: {raw_text}")

    return decision
