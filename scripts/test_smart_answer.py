from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.smart_answer import (
    build_smart_answer_prompt,
    extract_grounding_facts,
    generate_smart_answer,
)


def main() -> None:
    old_gemini = os.environ.pop("GEMINI_API_KEY", None)
    old_google = os.environ.pop("GOOGLE_API_KEY", None)
    old_disable_local = os.environ.get("LOGISTICS_AGENT_DISABLE_LOCAL_SECRETS")
    os.environ["LOGISTICS_AGENT_DISABLE_LOCAL_SECRETS"] = "1"

    try:
        payload = {
            "decision": "needs_more_information",
            "detected_intent": "shopping",
            "agents_called": ["shopping_agent"],
            "_extracted_items": [
                {"quantity": "20", "item": "laptops"},
                {"quantity": "10", "item": "tablets"},
            ],
            "_budget": {"amount": 12000.0, "currency": "USD"},
            "_excluded_supplier_countries": ["China"],
            "_parsed_report": {
                "status": "needs_more_information",
                "selected_suppliers": 0,
                "shortlisted_supplier_options": 0,
                "budget_limit_usd": 12000.0,
            },
            "_raw_report_text": "SHOPPING AGENT REPORT\\nSelected suppliers: 0\\nBudget limit: 12000.0 USD",
        }

        fallback = "No suppliers were shortlisted. More structured product details are needed."

        facts = extract_grounding_facts(payload)

        assert facts["decision"] == "needs_more_information"
        assert facts["_budget"]["amount"] == 12000.0
        assert "generated_agent_report_excerpt" in facts

        prompt = build_smart_answer_prompt(
            question="I need 20 laptops and 10 tablets from India under 12000 USD. Avoid China.",
            payload=payload,
            fallback_answer=fallback,
        )

        assert "Do not invent supplier names" in prompt
        assert "20" in prompt
        assert "12000.0" in prompt

        result = generate_smart_answer(
            question="I need 20 laptops and 10 tablets from India under 12000 USD. Avoid China.",
            payload=payload,
            fallback_answer=fallback,
        )

        assert result["mode"] == "fallback"
        assert result["provider"] == "deterministic"
        assert result["status"] == "api_key_missing"
        assert result["answer"] == fallback

    finally:
        if old_gemini is not None:
            os.environ["GEMINI_API_KEY"] = old_gemini

        if old_google is not None:
            os.environ["GOOGLE_API_KEY"] = old_google

        if old_disable_local is None:
            os.environ.pop("LOGISTICS_AGENT_DISABLE_LOCAL_SECRETS", None)
        else:
            os.environ["LOGISTICS_AGENT_DISABLE_LOCAL_SECRETS"] = old_disable_local

    print("PASS: smart answer fallback and prompt grounding test passed")


if __name__ == "__main__":
    main()
