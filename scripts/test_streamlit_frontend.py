from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    module = importlib.import_module("app.streamlit_frontend")

    payload = module.get_sample_shopping_payload()

    assert payload.get("payload_type") == "compact_frontend_payload"
    assert payload.get("detected_intent") == "shopping"
    assert payload.get("backend_validation", {}).get("response_contract_valid") is True
    assert payload.get("logistics_visualizer", {}).get("status") == "available"

    assert module.humanize("review_required") == "Review Required"
    assert module.humanize("fcl_preferred") == "FCL Preferred"
    assert module.humanize(True) == "Yes"
    assert module.humanize(False) == "No"

    fake_payload = {
        "decision": "needs_more_information",
        "detected_intent": "shopping",
        "_question": "I need 20 laptops and 10 tablets from India under 12000 USD.",
        "_extracted_items": [
            {"quantity": "20", "item": "laptops"},
            {"quantity": "10", "item": "tablets"},
        ],
        "agents_called": ["shopping_agent"],
    }

    fallback_answer = module.build_fallback_answer(fake_payload)

    assert "shopping/procurement request" in fallback_answer
    assert "20 laptops" in fallback_answer
    assert "10 tablets" in fallback_answer

    extracted_items = module.extract_requested_items(
        "I need 20 laptops and 10 tablets from India under 12000 USD."
    )

    assert extracted_items
    assert extracted_items[0]["quantity"] == "20"

    assert hasattr(module, "render_payload")
    assert hasattr(module, "render_agent_answer")
    assert hasattr(module, "get_clean_headline")
    assert hasattr(module, "extract_answer_text")
    assert hasattr(module, "main")

    print("PASS: Streamlit frontend smoke test passed")


if __name__ == "__main__":
    main()
