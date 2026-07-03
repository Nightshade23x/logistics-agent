from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.document_parser import parse_trade_document
from app.document_service import run_document_agent_from_file, run_document_agent_from_text
from app.document_pair_service import run_document_pair_agent_from_files, run_document_pair_agent_from_texts


def test_parse_invoice():
    text = """
INVOICE

Invoice Number: INV-TEST-001
Supplier: Test Supplier
Buyer: Test Buyer
Origin Country: India
Destination Country: USA

Items:
1. TVs | Quantity: 50 | Unit Weight: 12 kg | Total Weight: 600 kg

Total Weight: 600 kg
Currency: USD
Total Value: 10000
"""

    parsed = parse_trade_document(text)

    assert parsed["document_type"] == "invoice"
    assert parsed["fields"]["invoice_number"] == "INV-TEST-001"
    assert parsed["fields"]["supplier"] == "Test Supplier"
    assert len(parsed["items"]) == 1
    assert parsed["items"][0]["name"] == "TVs"
    assert parsed["items"][0]["quantity"] == 50


def test_parse_packing_list_dimensions():
    text = """
PACKING LIST

Packing List Number: PL-TEST-001
Supplier: Test Supplier
Origin Country: India
Destination Country: USA

Packages:
1. TVs | Quantity: 50 | Length: 120 cm | Width: 20 cm | Height: 80 cm | Weight: 12 kg
"""

    parsed = parse_trade_document(text)

    assert parsed["document_type"] == "packing_list"
    assert parsed["fields"]["packing_list_number"] == "PL-TEST-001"
    assert len(parsed["items"]) == 1
    assert parsed["items"][0]["length"] == 120
    assert parsed["items"][0]["dimension_unit"] == "cm"


def test_document_agent_response_contract():
    text = """
INVOICE

Invoice Number: INV-TEST-002
Supplier: Test Supplier
Origin Country: India
Destination Country: USA

Items:
1. Scooters | Quantity: 5 | Unit Weight: 90 kg | Total Weight: 450 kg
"""

    response = run_document_agent_from_text(text)

    assert response["agent_name"] == "document_ai_agent"
    assert "status" in response
    assert "summary" in response
    assert "plan" in response
    assert "report" in response
    assert "handoff_payload" in response
    assert "handoff_requests" in response
    assert response["handoff_payload"]["items"][0]["name"] == "Scooters"


def test_document_agent_from_file():
    path = ROOT_DIR / "data" / "documents" / "sample_packing_list.txt"

    response = run_document_agent_from_file(path)

    assert response["agent_name"] == "document_ai_agent"
    assert response["plan"]["document_type"] == "packing_list"
    assert len(response["handoff_payload"]["items"]) >= 1



def test_document_pair_validation_matching_documents():
    invoice_text = """
INVOICE

Invoice Number: INV-PAIR-001
Supplier: Test Supplier
Origin Country: India
Destination Country: USA

Items:
1. TVs | Quantity: 50 | Unit Weight: 12 kg | Total Weight: 600 kg

Total Weight: 600 kg
Currency: USD
Total Value: 10000
"""

    packing_list_text = """
PACKING LIST

Packing List Number: PL-PAIR-001
Supplier: Test Supplier
Origin Country: India
Destination Country: USA

Packages:
1. TVs | Quantity: 50 | Length: 120 cm | Width: 20 cm | Height: 80 cm | Weight: 12 kg

Total Weight: 600 kg
"""

    response = run_document_pair_agent_from_texts(invoice_text, packing_list_text)

    assert response["agent_name"] == "document_ai_agent"
    assert response["status"] == "ready_for_review"
    assert response["handoff_payload"]["mismatch_count"] == 0
    assert len(response["handoff_payload"]["items"]) == 1


def test_document_pair_validation_detects_quantity_mismatch():
    invoice_text = """
INVOICE

Invoice Number: INV-PAIR-002
Supplier: Test Supplier
Origin Country: India
Destination Country: USA

Items:
1. TVs | Quantity: 50 | Unit Weight: 12 kg | Total Weight: 600 kg
"""

    packing_list_text = """
PACKING LIST

Packing List Number: PL-PAIR-002
Supplier: Test Supplier
Origin Country: India
Destination Country: USA

Packages:
1. TVs | Quantity: 40 | Length: 120 cm | Width: 20 cm | Height: 80 cm | Weight: 12 kg
"""

    response = run_document_pair_agent_from_texts(invoice_text, packing_list_text)

    assert response["status"] == "review_required"
    assert response["handoff_payload"]["mismatch_count"] >= 1
    assert any("quantity" in mismatch for mismatch in response["missing_information"])


def test_document_pair_agent_from_files():
    invoice_path = ROOT_DIR / "data" / "documents" / "sample_invoice.txt"
    packing_list_path = ROOT_DIR / "data" / "documents" / "sample_packing_list.txt"

    response = run_document_pair_agent_from_files(invoice_path, packing_list_path)

    assert response["agent_name"] == "document_ai_agent"
    assert "handoff_payload" in response
    assert "handoff_requests" in response


def main() -> None:
    test_parse_invoice()
    test_parse_packing_list_dimensions()
    test_document_agent_response_contract()
    test_document_agent_from_file()
    test_document_pair_validation_matching_documents()
    test_document_pair_validation_detects_quantity_mismatch()
    test_document_pair_agent_from_files()

    print("All document agent tests passed.")


if __name__ == "__main__":
    main()
