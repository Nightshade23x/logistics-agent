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

    question = "I need 20 laptops and 10 tablets from India under 12000 USD. Avoid China."

    extracted_items = module.extract_requested_items(question)

    assert {"quantity": "20", "item": "laptops"} in extracted_items
    assert {"quantity": "10", "item": "tablets"} in extracted_items
    assert not any(item["item"].lower() == "usd" for item in extracted_items)

    budget = module.extract_budget(question)

    assert budget["amount"] == 12000.0
    assert budget["currency"] == "USD"

    report = """
Shopping Agent status: needs_more_information. Selected 0 supplier option(s). Estimated procurement cost: 0.0 USD.
SHOPPING AGENT REPORT
Request ID: SHOP-TEXT-REQUEST Customer: Unknown Customer Destination country: None Status: needs_more_information
Selected suppliers: 0 Estimated total procurement cost: 0.0 USD Budget limit: 12000.0 USD Within budget: True
Overall risk level: unknown Overall risk score: 0/10
Excluded supplier countries: ['China']
"""

    parsed = module.parse_raw_shopping_report(report)

    assert parsed["status"] == "needs_more_information"
    assert parsed["selected_suppliers"] == 0
    assert parsed["budget_limit_usd"] == 12000.0
    assert parsed["excluded_supplier_countries"] == ["China"]

    fake_payload = {
        "decision": "needs_more_information",
        "detected_intent": "shopping",
        "_question": question,
        "_extracted_items": extracted_items,
        "_budget": budget,
        "_excluded_supplier_countries": ["China"],
        "_parsed_report": parsed,
        "agents_called": ["shopping_agent"],
    }

    fallback_answer = module.build_frontend_answer(fake_payload)

    assert "shopping/procurement request" in fallback_answer
    assert "20 laptops" in fallback_answer
    assert "10 tablets" in fallback_answer
    assert "12000 USD" in fallback_answer
    assert "No suppliers were shortlisted" in fallback_answer

    assert hasattr(module, "render_payload")
    assert hasattr(module, "render_agent_answer")
    assert hasattr(module, "render_procurement_summary")
    assert hasattr(module, "has_displayable_metrics")
    assert hasattr(module, "render_empty_state")
    assert module.has_displayable_metrics({"a": 1}) is True
    assert module.has_displayable_metrics({"a": None, "b": ""}) is False
    assert hasattr(module, "get_clean_headline")
    assert hasattr(module, "build_frontend_answer")
    assert hasattr(module, "generate_smart_answer")
    assert hasattr(module, "main")

    print("PASS: Streamlit frontend smoke test passed")


if __name__ == "__main__":
    main()
