from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_adapters.compliance_client import check_product_compliance
from app.partner_adapters.finance_client import calculate_landed_cost
from app.partner_adapters.risk_client import check_country_risk
from app.partner_adapters.trader_client import classify_trade_product
from app.response_contract_validator import (
    validate_agent_response,
    validate_user_agent_response,
)
from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json_file,
)


def _print_result(name: str, passed: bool, detail: str) -> None:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name} - {detail}")


def _check_user_agent_response(
    check_name: str,
    response: dict,
    expected_agents: list[str],
) -> bool:
    errors: list[str] = []

    contract_result = validate_user_agent_response(response)

    if not contract_result["is_valid"]:
        errors.extend(contract_result["errors"])

    agents_called = response.get("agents_called", [])

    for agent_name in expected_agents:
        if agent_name not in agents_called:
            errors.append(f"missing expected agent: {agent_name}")

    final_verdict = response.get("final_verdict", {})
    verdict = final_verdict.get("verdict")

    if not verdict:
        errors.append("missing final verdict")

    passed = len(errors) == 0

    if passed:
        _print_result(
            check_name,
            True,
            f"status={response.get('status')}, verdict={verdict}, contract=valid",
        )
    else:
        _print_result(check_name, False, "; ".join(errors))

    return passed


def _run_shopping_json_flow() -> bool:
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    return _check_user_agent_response(
        check_name="Shopping JSON flow",
        response=response,
        expected_agents=[
            "shopping_agent",
            "logistics_agent",
            "partner_review_service",
        ],
    )


def _run_document_to_logistics_flow() -> bool:
    response = run_user_agent_from_files(
        [
            ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
            ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
        ]
    )

    return _check_user_agent_response(
        check_name="Document to Logistics flow",
        response=response,
        expected_agents=[
            "document_ai_agent",
            "logistics_agent",
            "partner_review_service",
        ],
    )


def _run_logistics_json_flow() -> bool:
    temporary_request_path = ROOT_DIR / "data" / "tmp_health_logistics_request.json"

    logistics_request = {
        "shipment_id": "HEALTH-LOG-001",
        "customer": "Health Check Customer",
        "origin": "India",
        "destination": "USA",
        "items": [
            {
                "name": "TVs",
                "quantity": 10,
                "length": 120,
                "width": 20,
                "height": 80,
                "dimension_unit": "cm",
                "weight": 12,
                "weight_unit": "kg",
                "fragile": True,
                "stackable": False,
            },
            {
                "name": "Ceramic tiles",
                "quantity": 50,
                "length": 60,
                "width": 60,
                "height": 8,
                "dimension_unit": "cm",
                "weight": 12,
                "weight_unit": "kg",
                "fragile": True,
                "stackable": True,
            },
        ],
    }

    try:
        temporary_request_path.write_text(
            json.dumps(logistics_request, indent=2),
            encoding="utf-8",
        )

        response = run_user_agent_from_json_file(temporary_request_path)

        return _check_user_agent_response(
            check_name="Logistics JSON flow",
            response=response,
            expected_agents=[
                "logistics_agent",
                "partner_review_service",
            ],
        )

    finally:
        if temporary_request_path.exists():
            temporary_request_path.unlink()


def _check_partner_adapter_response(name: str, response: dict) -> tuple[bool, str]:
    contract_result = validate_agent_response(response, context=name)

    if not contract_result["is_valid"]:
        return False, "; ".join(contract_result["errors"])

    if response.get("status") != "not_configured":
        return False, f"expected not_configured, got {response.get('status')}"

    return True, "contract=valid, status=not_configured"


def _run_partner_adapter_checks() -> bool:
    checks = {
        "Risk adapter": check_country_risk(destination_country="USA"),
        "Compliance adapter": check_product_compliance(
            product_name="TVs",
            destination_country="USA",
            origin_country="India",
            product_category="electronics",
        ),
        "Trader adapter": classify_trade_product(
            product_name="TVs",
            origin_country="India",
            destination_country="USA",
            product_category="electronics",
            declared_value_usd=1000,
        ),
        "Finance adapter": calculate_landed_cost(
            origin_country="India",
            destination_country="USA",
            total_cbm=10,
            total_weight_kg=1000,
            declared_value_usd=1000,
        ),
    }

    all_passed = True

    for check_name, response in checks.items():
        passed, detail = _check_partner_adapter_response(check_name, response)
        _print_result(check_name, passed, detail)
        all_passed = all_passed and passed

    return all_passed


def main() -> None:
    print("SYSTEM HEALTH CHECK")
    print("=" * 30)

    checks = [
        _run_shopping_json_flow(),
        _run_document_to_logistics_flow(),
        _run_logistics_json_flow(),
        _run_partner_adapter_checks(),
    ]

    print()

    if all(checks):
        print("System health check passed.")
        return

    print("System health check failed.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
