from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

TEST_COMMANDS = [
    [sys.executable, "scripts/test_partner_adapters.py"],
    [sys.executable, "scripts/test_partner_config.py"],
    [sys.executable, "scripts/test_backend_status.py"],
    [sys.executable, "scripts/test_response_contract_validator.py"],
    [sys.executable, "scripts/test_partner_review_service.py"],
    [sys.executable, "scripts/test_partner_review_payload_validator.py"],
    [sys.executable, "scripts/test_partner_request_builder.py"],
    [sys.executable, "scripts/test_partner_review_request_builder_integration.py"],
    [sys.executable, "scripts/test_final_verdict.py"],
    [sys.executable, "scripts/test_frontend_payload.py"],
    [sys.executable, "scripts/test_frontend_cleanup_authority_v20.py"],
    [sys.executable, "scripts/test_explicit_total_weight_units_v21.py"],
    [sys.executable, "scripts/test_cargo_name_weight_precision_v22.py"],
    [sys.executable, "scripts/test_container_visualizer_status_gate_v23.py"],
    [sys.executable, "scripts/test_readiness_fitcheck_consistency_v24.py"],
    [sys.executable, "scripts/test_fragile_stackable_visual_units_v25.py"],
    [sys.executable, "scripts/test_loading_sequence_fallback_v26.py"],
    [sys.executable, "scripts/test_canonical_destination_authority_v27.py"],
    [sys.executable, "scripts/test_per_unit_imperial_weight_v28.py"],
    [sys.executable, "scripts/test_final_weight_authority_v32.py"],
    [sys.executable, "scripts/test_logistics_intent_authority_v33.py"],
    [sys.executable, "scripts/test_demo_examples_v34.py"],
    [sys.executable, "scripts/test_demo_answers_and_ui_v35.py"],
    [sys.executable, "scripts/test_completed_landed_cost_answer_v36.py"],
    [sys.executable, "scripts/test_backend_service.py"],
    [sys.executable, "scripts/test_backend_service_payload_validator.py"],
    [sys.executable, "scripts/test_clarification_questions.py"],
    [sys.executable, "scripts/test_shopping_quality_review.py"],
    [sys.executable, "scripts/test_procurement_advisor.py"],
    [sys.executable, "scripts/test_logistics_quality_review.py"],
    [sys.executable, "scripts/test_cargo_special_handling.py"],
    [sys.executable, "scripts/test_freight_mode_advisor.py"],
    [sys.executable, "scripts/test_trade_terms_advisor.py"],
    [sys.executable, "scripts/test_insurance_advisor.py"],
    [sys.executable, "scripts/test_landed_cost_advisor.py"],
    [sys.executable, "scripts/test_trade_compliance_readiness_advisor.py"],
    [sys.executable, "scripts/test_booking_readiness_advisor.py"],
    [sys.executable, "scripts/test_document_quality_review.py"],
    [sys.executable, "scripts/test_document_requirements_advisor.py"],
    [sys.executable, "scripts/test_output_text_cleaner.py"],
    [sys.executable, "scripts/test_executive_summary_builder.py"],
    [sys.executable, "scripts/test_ui_sections_builder.py"],
    [sys.executable, "scripts/test_compact_frontend_payload.py"],
    [sys.executable, "scripts/test_demo_report_builder.py"],
    [sys.executable, "scripts/test_export_demo_pack.py"],
    [sys.executable, "scripts/test_final_answer_builder.py"],
    [sys.executable, "scripts/test_action_plan_builder.py"],
    [sys.executable, "scripts/test_text_request_intent.py"],
    [sys.executable, "scripts/test_user_agent.py"],
    [sys.executable, "scripts/test_shopping_agent.py"],
    [sys.executable, "scripts/test_document_agent.py"],
    [sys.executable, "scripts/test_direct_volume_end_to_end.py"],
    [sys.executable, "scripts/test_logistics_agent.py"],
    [sys.executable, "scripts/system_health_check.py"],
    [sys.executable, "scripts/test_text_shipment_parser_multi_item.py"],
    [sys.executable, "scripts/test_container_planning_multi_item_consistency.py"],
    [sys.executable, "scripts/test_empty_state_simple_tabs_v38.py"],
    [sys.executable, "scripts/test_ease_of_access_guided_workflow_v39.py"],
    [sys.executable, "scripts/test_llm_request_interpreter_v40.py"],
    [sys.executable, "scripts/test_prompt_robustness_backend_gate_v41.py"],
    [sys.executable, "scripts/test_local_shipment_repair_v42.py"],
    [sys.executable, "scripts/test_gemini_json_resilience_v43.py"],
    [sys.executable, "scripts/test_adversarial_input_authority_v44.py"],
    [sys.executable, "scripts/test_rule_router_fallback_v45.py"],
    [sys.executable, "scripts/test_parser_robustness_v47.py"],
    [sys.executable, "scripts/test_remaining_backend_robustness_v48.py"],
]


def main() -> None:
    print("RUNNING FULL LOCAL TEST SUITE")
    print("=" * 40)

    failed_commands = []

    for command in TEST_COMMANDS:
        command_text = " ".join(command)
        print("")
        print(f"> {command_text}")
        print("-" * 40)

        result = subprocess.run(command, cwd=ROOT_DIR)

        if result.returncode != 0:
            failed_commands.append(command_text)

    print("")
    print("=" * 40)

    if failed_commands:
        print("FAILED TEST COMMANDS")
        for command in failed_commands:
            print(f"- {command}")
        raise SystemExit(1)

    print("All tests passed.")


if __name__ == "__main__":
    main()

# RUN_INTEGRATION_UX_FOUNDATION_V37
if __name__ == "__main__":
    import subprocess as _v37_subprocess
    import sys as _v37_sys

    _v37_completed = _v37_subprocess.run(
        [_v37_sys.executable, "scripts/test_integration_ux_foundation_v37.py"],
        check=False,
    )
    if _v37_completed.returncode != 0:
        raise SystemExit(_v37_completed.returncode)
