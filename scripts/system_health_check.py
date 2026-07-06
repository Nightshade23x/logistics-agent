from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.partner_adapters.compliance_client import check_product_compliance
from app.partner_adapters.finance_client import calculate_landed_cost
from app.partner_adapters.risk_client import check_country_risk
from app.partner_adapters.trader_client import classify_trade_product
from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json,
    run_user_agent_from_json_file,
)


def _status_line(name: str, passed: bool, detail: str = "") -> None:
    marker = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{marker}] {name}{suffix}")


def _check_shopping_json_flow() -> bool:
    response = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    passed = (
        response.get("detected_intent") == "shopping"
        and "shopping_agent" in response.get("agents_called", [])
        and "logistics_agent" in response.get("agents_called", [])
        and "partner_review_service" in response.get("agents_called", [])
        and "final_verdict" in response
    )

    _status_line(
        "Shopping JSON flow",
        passed,
        f"status={response.get('status')}, verdict={response.get('final_verdict', {}).get('verdict')}",
    )
    return passed


def _check_document_flow() -> bool:
    response = run_user_agent_from_files(
        [
            ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
            ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
        ]
    )

    passed = (
        response.get("detected_intent") == "document"
        and "document_ai_agent" in response.get("agents_called", [])
        and "logistics_agent" in response.get("agents_called", [])
        and "partner_review_service" in response.get("agents_called", [])
        and "final_verdict" in response
    )

    _status_line(
        "Document to Logistics flow",
        passed,
        f"status={response.get('status')}, verdict={response.get('final_verdict', {}).get('verdict')}",
    )
    return passed


def _check_logistics_json_flow() -> bool:
    response = run_user_agent_from_json(
        {
            "shipment_id": "HEALTH-LOG-001",
            "customer": "Health Check",
            "origin": "India",
            "destination": "USA",
            "declared_value_usd": 18500.0,
            "items": [
                {
                    "name": "TVs",
                    "quantity": 10,
                    "length_cm": 120,
                    "width_cm": 20,
                    "height_cm": 80,
                    "weight_kg": 12,
                }
            ],
        }
    )

    passed = (
        response.get("detected_intent") == "logistics"
        and "logistics_agent" in response.get("agents_called", [])
        and "partner_review_service" in response.get("agents_called", [])
        and "final_verdict" in response
    )

    _status_line(
        "Logistics JSON flow",
        passed,
        f"status={response.get('status')}, verdict={response.get('final_verdict', {}).get('verdict')}",
    )
    return passed


def _check_partner_adapters() -> bool:
    responses = [
        check_country_risk("USA"),
        check_product_compliance(
            product_name="TVs",
            product_category="electronics",
            origin_country="India",
            destination_country="USA",
        ),
        classify_trade_product(
            product_name="TVs",
            product_category="electronics",
            origin_country="India",
            destination_country="USA",
            declared_value_usd=10000.0,
        ),
        calculate_landed_cost(
            origin_country="India",
            destination_country="USA",
            total_cbm=5.0,
            total_weight_kg=500.0,
            declared_value_usd=10000.0,
        ),
    ]

    passed = all(response.get("status") == "not_configured" for response in responses)

    _status_line(
        "Partner adapter skeletons",
        passed,
        "expected not_configured until live MCP/REST details are available",
    )
    return passed


def main() -> None:
    print("SYSTEM HEALTH CHECK")
    print("=" * 30)

    checks = [
        _check_shopping_json_flow(),
        _check_document_flow(),
        _check_logistics_json_flow(),
        _check_partner_adapters(),
    ]

    print("")
    if all(checks):
        print("System health check passed.")
        raise SystemExit(0)

    print("System health check failed.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
