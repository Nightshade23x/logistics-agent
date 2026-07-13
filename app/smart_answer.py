from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

ROOT_DIR = Path(__file__).resolve().parents[1]
LOCAL_SECRETS_ENV = ROOT_DIR / "config" / "local_secrets.env"


def read_local_secret(name: str) -> str:
    if os.environ.get("LOGISTICS_AGENT_DISABLE_LOCAL_SECRETS") == "1":
        return ""

    if not LOCAL_SECRETS_ENV.exists():
        return ""

    for line in LOCAL_SECRETS_ENV.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)

        if key.strip() != name:
            continue

        return value.strip().strip('"').strip("'")

    return ""


def get_gemini_api_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or read_local_secret("GEMINI_API_KEY")
        or read_local_secret("GOOGLE_API_KEY")
        or ""
    ).strip()


def get_gemini_model() -> str:
    return (
        os.environ.get("GEMINI_MODEL")
        or read_local_secret("GEMINI_MODEL")
        or DEFAULT_GEMINI_MODEL
    ).strip() or DEFAULT_GEMINI_MODEL


def _trim_text(value: Any, max_chars: int = 2500) -> str:
    text = str(value or "").strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "\n...[trimmed]"


def extract_grounding_facts(payload: dict[str, Any]) -> dict[str, Any]:
    selected_keys = [
        "decision",
        "detected_intent",
        "agents_called",
        "partner_review_status",
        "logistics_metrics",
        "booking_readiness",
        "action_plan",
        "backend_validation",
        "_extracted_items",
        "_budget",
        "_preferred_supplier_countries",
        "_excluded_supplier_countries",
        "_parsed_report",
    ]

    facts: dict[str, Any] = {}

    for key in selected_keys:
        value = payload.get(key)

        if value not in [None, "", [], {}]:
            facts[key] = value

    raw_report = payload.get("_raw_report_text")

    if raw_report:
        facts["generated_agent_report_excerpt"] = _trim_text(raw_report, max_chars=700)

    return facts


def build_smart_answer_prompt(
    *,
    question: str,
    payload: dict[str, Any],
    fallback_answer: str,
) -> str:
    facts = extract_grounding_facts(payload)

    return f"""You are writing the final answer for a logistics/procurement dashboard.

Rules:
- Use only the facts in BACKEND_FACTS.
- Do not invent supplier names, prices, logistics metrics, container plans, HS codes, duties, or risks.
- If the backend did not shortlist suppliers, say that clearly.
- If logistics did not run, say that logistics needs selected supplier/item data first.
- Give a concise, useful answer in plain English.
- Include next steps.
- Do not mention raw JSON or internal implementation details.
- Do not apologize.

USER_QUESTION:
{question}

DETERMINISTIC_FALLBACK_ANSWER:
{fallback_answer}

BACKEND_FACTS:
{json.dumps(facts, indent=2, ensure_ascii=False)}

Write the user-facing answer now.
"""


def _parse_gemini_text(response_payload: dict[str, Any]) -> str:
    candidates = response_payload.get("candidates") or []

    if not candidates:
        return ""

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []

    texts = []

    for part in parts:
        text = part.get("text")

        if text:
            texts.append(text)

    return "\n".join(texts).strip()


def call_gemini_generate_content(
    *,
    prompt: str,
    api_key: str,
    model: str,
    timeout_seconds: int = 30,
) -> str:
    endpoint = GEMINI_ENDPOINT_TEMPLATE.format(model=model)

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 350,
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_body = response.read().decode("utf-8", errors="replace")

    response_payload = json.loads(response_body)
    return _parse_gemini_text(response_payload)


def generate_smart_answer(
    *,
    question: str,
    payload: dict[str, Any],
    fallback_answer: str,
) -> dict[str, Any]:
    api_key = get_gemini_api_key()
    model = get_gemini_model()

    if not api_key:
        return {
            "mode": "fallback",
            "provider": "deterministic",
            "model": None,
            "status": "api_key_missing",
            "answer": fallback_answer,
            "note": "Set GEMINI_API_KEY to enable Gemini smart-answer synthesis.",
        }

    prompt = build_smart_answer_prompt(
        question=question,
        payload=payload,
        fallback_answer=fallback_answer,
    )

    try:
        answer = call_gemini_generate_content(
            prompt=prompt,
            api_key=api_key,
            model=model,
        )
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        retry_after = exc.headers.get("Retry-After") if exc.headers else None

        status = f"http_error_{exc.code}"

        if exc.code == 429:
            status = "quota_or_rate_limit_429"

        return {
            "mode": "fallback",
            "provider": "gemini",
            "model": model,
            "status": status,
            "answer": fallback_answer,
            "error": _trim_text(error_body, max_chars=900),
            "retry_after_seconds": retry_after,
        }
    except Exception as exc:
        return {
            "mode": "fallback",
            "provider": "gemini",
            "model": model,
            "status": "request_failed",
            "answer": fallback_answer,
            "error": str(exc),
        }

    if not answer:
        return {
            "mode": "fallback",
            "provider": "gemini",
            "model": model,
            "status": "empty_response",
            "answer": fallback_answer,
        }

    return {
        "mode": "gemini",
        "provider": "gemini",
        "model": model,
        "status": "generated",
        "answer": answer,
    }
