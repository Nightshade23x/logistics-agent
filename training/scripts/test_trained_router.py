from __future__ import annotations

import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_PATH = Path("G:/ai-models/checkpoints/router-qwen-0.5b-lora-150/final_adapter")

SYSTEM_PROMPT = """
You are the User Agent router for a trade and logistics multi-agent system.
Return only valid JSON.
Use only these agents:
shopping_agent, document_ai_agent, logistics_agent.
Do not invent agents.
"""


def build_prompt(tokenizer, user_text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_text},
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

def load_model():
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(
        ADAPTER_PATH,
        trust_remote_code=True,
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=dtype,
        trust_remote_code=True,
    )

    model = PeftModel.from_pretrained(
        base_model,
        ADAPTER_PATH,
    )

    if torch.cuda.is_available():
        model = model.to("cuda")

    model.eval()
    return model, tokenizer

def generate_response(model, tokenizer, user_text: str) -> str:
    prompt = build_prompt(tokenizer, user_text)

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    )

    if torch.cuda.is_available():
        inputs = {key: value.to("cuda") for key, value in inputs.items()}

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=180,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


def try_parse_json(text: str) -> None:
    print("RAW MODEL OUTPUT")
    print("=" * 40)
    print(text)
    print("")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        print("JSON VALID: False")
        print(f"JSON error: {error}")
        return

    print("JSON VALID: True")
    print(json.dumps(parsed, indent=2))


def main() -> None:
    model, tokenizer = load_model()

    test_prompts = [
        "I need 50 TVs, 5 scooters, and 100 ceramic tiles from India. Avoid China. Budget 13000 USD.",
        "I uploaded an invoice and packing list. Check if they match and create a shipping plan.",
        "What container do I need for 19 CBM and 2250 kg?",
        "Can you help me?",
    ]

    for index, prompt in enumerate(test_prompts, start=1):
        print("")
        print("#" * 80)
        print(f"TEST {index}")
        print("#" * 80)
        print(f"USER: {prompt}")
        print("")

        response = generate_response(model, tokenizer, prompt)
        try_parse_json(response)


if __name__ == "__main__":
    main()
