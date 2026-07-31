from __future__ import annotations

from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_text_request
from app.text_shipment_parser import parse_shipment_text
from app.user_agent import run_user_agent_from_text


DIRECT_PROMPT = (
    "Ship 10 cubic feet of tiles from India to USA."
)
EXPECTED_CBM = 0.28316846592


def close(actual, expected, tolerance=5e-5):
    return abs(float(actual) - float(expected)) <= tolerance


def test_internal_parser_and_user_agent():
    parsed = parse_shipment_text(DIRECT_PROMPT)
    item = parsed["items"][0]

    assert close(parsed["total_cbm"], EXPECTED_CBM), parsed
    assert close(item["total_cbm"], EXPECTED_CBM), item
    assert item["source_volume"] == 10, item
    assert item["source_volume_unit"] == "cubic feet", item

    response = run_user_agent_from_text(DIRECT_PROMPT)

    assert response["detected_intent"] == "logistics", response
    assert "logistics_agent" in response["agents_called"], response
    assert close(
        response["handoff_payload"]["total_cbm"],
        EXPECTED_CBM,
    ), response
    assert response["handoff_payload"]["total_weight_kg"] == 0, response


def test_browser_payload_uses_unknown_weight_semantics():
    payload = process_text_request(DIRECT_PROMPT)

    measurement = payload["cargo_measurement_status"]
    metrics = payload["logistics_metrics"]
    visualizer = payload["logistics_visualizer"]
    container = visualizer["container"]
    fit = visualizer["fit_check"]
    cargo = visualizer["cargo_mix"]

    assert payload["status"] == (
        "partial_plan_needs_more_information"
    ), payload

    assert measurement["volume_known"] is True, measurement
    assert measurement["weight_known"] is False, measurement
    assert measurement["packed_dimensions_known"] is False, measurement

    assert close(metrics["total_cbm"], EXPECTED_CBM), metrics
    assert metrics["total_weight_kg"] is None, metrics
    assert metrics["weight_known"] is False, metrics
    assert metrics["readiness_status"] == (
        "needs_cargo_weight_and_dimensions"
    ), metrics

    assert container["total_weight_kg"] is None, container
    assert container["risk_level"] == metrics["risk_level"], (
        container,
        metrics,
    )
    assert container["risk_score"] == metrics["risk_score"], (
        container,
        metrics,
    )

    assert fit["status"] == (
        "volume_fits_payload_unverified"
    ), fit
    assert fit["item_fit_results"] == [], fit
    assert any(
        "payload fit cannot be verified" in warning.lower()
        for warning in fit["warnings"]
    ), fit
    assert any(
        "packed dimensions" in warning.lower()
        for warning in fit["warnings"]
    ), fit

    assert len(cargo) == 1, cargo
    item = cargo[0]

    assert item["weight_known"] is False, item
    assert item["packed_dimensions_known"] is False, item
    assert item["total_weight_kg"] is None, item
    assert item["dimension_source"] == (
        "advisory aggregate-volume representation"
    ), item

    tags = {
        str(tag).strip().lower()
        for tag in item.get("category_tags", [])
    }
    assert "heavy" not in tags, item


def test_complete_shipments_are_unchanged():
    multi_prompt = (
        "Ship 2 CBM pumps weighing 500 kg, "
        "3 CBM valves weighing 300 kg and "
        "1 CBM seals weighing 50 kg from India to USA."
    )

    heavy_prompt = (
        "Ship 10 CBM ceramic tiles weighing 20000 kg "
        "from India to USA."
    )

    full_trade_prompt = (
        "Create a full trade plan for 10 CBM ceramic tiles "
        "from India to USA using CIF. Total weight is 1200 kg. "
        "Include logistics, documents, duty, and risk."
    )

    multi = process_text_request(multi_prompt)
    heavy = process_text_request(heavy_prompt)
    full_trade = process_text_request(full_trade_prompt)

    assert multi["logistics_metrics"]["total_cbm"] == 6, multi
    assert multi["logistics_metrics"]["total_weight_kg"] == 850, multi

    assert heavy["logistics_metrics"]["total_weight_kg"] == 20000, heavy
    assert full_trade["logistics_metrics"]["total_weight_kg"] == 1200, (
        full_trade
    )
    assert (
        full_trade["logistics_visualizer"]["container"]["total_weight_kg"]
        == 1200
    ), full_trade


def main():
    test_internal_parser_and_user_agent()
    test_browser_payload_uses_unknown_weight_semantics()
    test_complete_shipments_are_unchanged()

    print("PASS - cubic-feet conversion remains 0.2832 CBM")
    print("PASS - missing weight is represented as not confirmed")
    print("PASS - payload and package fit remain explicitly unverified")
    print("PASS - advisory geometry is not called packed dimensions")
    print("PASS - risk fields remain internally consistent")
    print("PASS - multi-item, heavy, and full-trade totals remain unchanged")


if __name__ == "__main__":
    main()
