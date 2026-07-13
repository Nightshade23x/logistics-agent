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

    structured_payload = {
        "decision": "review_required",
        "detected_intent": "shopping",
        "agents_called": ["shopping_agent", "logistics_agent", "partner_review_service"],
        "partner_review_status": "partner_review_not_configured",
        "logistics_metrics": {
            "total_cbm": 19.41,
            "total_weight_kg": 2250.0,
            "recommended_container": "20ft Standard Container",
            "risk_level": "high",
        },
        "booking_readiness": {
            "score": 40,
            "ready_for_first_pass": True,
            "ready_for_booking": False,
            "next_gate": "fill_missing_information",
        },
    }

    structured_answer = module.build_frontend_answer(structured_payload)

    assert "review_required" not in structured_answer
    assert "partner_review_service" not in structured_answer
    assert "Review Required" in structured_answer
    assert "20ft Standard Container" in structured_answer

    fallback_answer = module.build_frontend_answer(fake_payload)

    assert "shopping/procurement request" in fallback_answer


    guided_request = module.build_guided_request_text(
        {
            "items": [
                {"quantity": "50", "item": "TVs"},
                {"quantity": "5", "item": "scooters"},
                {"quantity": "100", "item": "ceramic tiles"},
            ],
            "origin_country": "India",
            "destination_country": "USA",
            "preferred_supplier_country": "India",
            "avoid_countries": "China",
            "budget_amount": "13000",
            "budget_currency": "USD",
            "incoterm": "FOB",
            "dimensions": "TV 120x70x15 cm",
            "weights": "TV 18 kg each",
            "freight_quote_usd": "1800",
            "insurance_premium_usd": "150",
            "duty_rate_percent": "5",
            "import_tax_rate_percent": "16",
            "notes": "fragile cargo",
        }
    )

    assert "50 TVs" in guided_request
    assert "5 scooters" in guided_request
    assert "100 ceramic tiles" in guided_request
    assert "Avoid supplier countries: China" in guided_request
    assert "Budget is 13000 USD" in guided_request
    assert "Incoterm / trade term: FOB" in guided_request

    missing_payload = {
        "decision": "needs_more_information",
        "booking_readiness": {
            "ready_for_booking": False,
            "missing_inputs": ["freight_quote_usd", "insurance_premium_usd"],
        },
    }

    assert module.infer_booking_status(missing_payload) == "Needs More Information"
    missing_items = [item.lower() for item in module.frontend_collect_missing_items(missing_payload)]

    assert any("freight" in item and "quote" in item for item in missing_items)


    known_fields = module.infer_known_request_fields(
        "Origin country: India. Destination country: USA. Incoterm / trade term: FOB. "
        "Item dimensions: TV 120x70x15 cm. Item weights: TV 18 kg each. "
        "Freight quote: 1800 USD. Insurance premium: 150 USD. Duty rate: 5%. Import tax rate: 16%."
    )

    assert known_fields["origin_country"] is True
    assert known_fields["destination_country"] is True
    assert known_fields["incoterm"] is True
    assert known_fields["item_dimensions"] is True
    assert known_fields["item_weights"] is True
    assert known_fields["freight_quote_usd"] is True
    assert known_fields["insurance_premium_usd"] is True
    assert known_fields["duty_rate_percent"] is True
    assert known_fields["import_tax_rate_percent"] is True

    mapped_fields = module.missing_text_to_field_ids(
        ["Freight quote USD", "Insurance premium USD", "Duty rate percent", "Import tax rate percent"]
    )

    assert "freight_quote_usd" in mapped_fields
    assert "insurance_premium_usd" in mapped_fields
    assert "duty_rate_percent" in mapped_fields
    assert "import_tax_rate_percent" in mapped_fields
    assert "20 laptops" in fallback_answer
    assert "10 tablets" in fallback_answer
    assert "12000 USD" in fallback_answer
    assert "No suppliers were shortlisted" in fallback_answer

    assert hasattr(module, "render_payload")
    assert hasattr(module, "render_agent_answer")
    assert hasattr(module, "render_procurement_summary")
    assert hasattr(module, "has_displayable_metrics")
    assert hasattr(module, "render_empty_state")
    assert hasattr(module, "inject_app_styles")
    assert hasattr(module, "render_app_header")
    assert hasattr(module, "render_kpi_grid")
    assert hasattr(module, "render_stage_tracker")
    assert hasattr(module, "apply_partner_runtime_settings")
    assert hasattr(module, "render_agent_connection_summary")
    assert hasattr(module, "run_frontend_flow")
    assert hasattr(module, "render_last_run_status")
    assert hasattr(module, "run_live_partner_health_check")
    assert module.chip_class("ready_for_review") == "good"
    assert module.chip_class("needs_more_information") == "warn"
    assert module.chip_class("critical_review_required") == "bad"
    assert module.classify_action_item("Confirm the Incoterm before booking") == "Trade Terms"
    assert module.classify_action_item("Freight Quote USD") == "Cost Inputs"
    assert module.classify_action_item("Document: Commercial Invoice") == "Documents"
    assert module.classify_action_item("Logistics risk level is high") == "Cargo & Risk"
    assert module.has_displayable_metrics({"a": 1}) is True
    assert module.has_displayable_metrics({"a": None, "b": ""}) is False
    assert hasattr(module, "get_clean_headline")
    assert hasattr(module, "build_frontend_answer")
    assert hasattr(module, "build_structured_run_answer")
    assert hasattr(module, "build_followup_question_with_missing_info")
    assert hasattr(module, "render_missing_information_form")
    assert hasattr(module, "build_guided_request_text")
    assert hasattr(module, "frontend_collect_missing_items")
    assert hasattr(module, "infer_booking_status")
    assert hasattr(module, "render_frontend_action_center")
    assert hasattr(module, "infer_known_request_fields")
    assert hasattr(module, "missing_text_to_field_ids")
    assert hasattr(module, "user_fillable_missing_fields")
    assert hasattr(module, "infer_next_frontend_action")
    assert hasattr(module, "workflow_step_states")
    assert hasattr(module, "render_workflow_guide")
    assert hasattr(module, "generate_smart_answer")
    assert hasattr(module, "main")

    print("PASS: Streamlit frontend smoke test passed")


if __name__ == "__main__":
    main()
