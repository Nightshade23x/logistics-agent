from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.ui_sections_builder import build_ui_sections


def test_ui_sections_from_shopping_json_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    sections = build_ui_sections(payload)

    assert isinstance(sections, list)
    assert len(sections) >= 7

    section_ids = {section["section_id"] for section in sections}

    assert "executive_decision" in section_ids
    assert "shipment_snapshot" in section_ids
    assert "procurement" in section_ids
    assert "logistics" in section_ids
    assert "compliance_documents" in section_ids
    assert "costs_insurance" in section_ids
    assert "partner_checks" in section_ids
    assert "next_actions" in section_ids


def test_ui_sections_in_backend_payload():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    assert "ui_sections" in payload
    assert isinstance(payload["ui_sections"], list)
    assert payload["ui_sections"]

    first_section = payload["ui_sections"][0]

    assert first_section["section_id"] == "executive_decision"
    assert "ready_for_first_pass" in first_section["metrics"]


def test_ui_sections_have_required_card_keys():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    for section in payload["ui_sections"]:
        assert "section_id" in section
        assert "title" in section
        assert "status" in section
        assert "summary" in section
        assert "metrics" in section
        assert "bullets" in section
        assert "actions" in section


def main() -> None:
    test_ui_sections_from_shopping_json_payload()
    test_ui_sections_in_backend_payload()
    test_ui_sections_have_required_card_keys()

    print("All UI sections builder tests passed.")


if __name__ == "__main__":
    main()
