from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import api_server

from app.backend_service import process_text_request
from app.frontend_response_cleanup import cleanup_frontend_response
from app.text_shipment_parser import parse_shipment_text


NO_OF_KG = (
    "Ship 10 CBM ceramic tiles from India to USA. "
    "Total weight is 2200.5 kg."
)

WITH_OF_KG = (
    "Ship 10 CBM of ceramic tiles from India to USA. "
    "Total weight is 2200.5 kg."
)

POUNDS = (
    "Ship 10 CBM ceramic tiles from India to USA. "
    "Total weight is 2204.62 lb."
)

FULL_TRADE_POUNDS = (
    "Create a full trade plan for 10 CBM ceramic tiles "
    "from India to USA using CIF. "
    "Total weight is 2,204.62 pounds. "
    "Include logistics, documents, duty, and risk."
)


def metrics(payload):
    return payload.get("logistics_metrics") or {}


def visualizer(payload):
    return payload.get("logistics_visualizer") or {}


def container(payload):
    return visualizer(payload).get("container") or {}


def cargo(payload):
    return visualizer(payload).get("cargo_mix") or []


def assert_single_tiles(payload, expected_weight):
    items = cargo(payload)
    assert len(items) == 1, items

    item = items[0]
    assert item.get("item_name") == "ceramic tiles", item
    assert item.get("quantity") == 1, item
    assert item.get("total_cbm") == 10, item
    assert item.get("total_weight_kg") == expected_weight, item
    assert item.get("unit_weight_kg") == expected_weight, item


def test_cbm_name_without_of():
    parsed = parse_shipment_text(NO_OF_KG)
    assert parsed["items"][0]["name"] == "ceramic tiles", parsed

    payload = process_text_request(NO_OF_KG)
    assert metrics(payload)["total_cbm"] == 10, metrics(payload)
    assert metrics(payload)["total_weight_kg"] == 2200.5, metrics(payload)
    assert_single_tiles(payload, 2200.5)


def test_cbm_name_with_of_stays_correct():
    payload = process_text_request(WITH_OF_KG)
    assert metrics(payload)["total_cbm"] == 10, metrics(payload)
    assert metrics(payload)["total_weight_kg"] == 2200.5, metrics(payload)
    assert_single_tiles(payload, 2200.5)


def test_converted_weight_is_practical_precision():
    for prompt in (POUNDS, FULL_TRADE_POUNDS):
        payload = process_text_request(prompt)

        assert metrics(payload)["total_weight_kg"] == 1000.0, metrics(payload)
        assert container(payload)["total_weight_kg"] == 1000.0, container(payload)
        assert_single_tiles(payload, 1000.0)

        cleaned = cleanup_frontend_response(deepcopy(payload), prompt)
        assert metrics(cleaned)["total_weight_kg"] == 1000.0, metrics(cleaned)
        assert container(cleaned)["total_weight_kg"] == 1000.0, container(cleaned)

    routed = api_server.request_text(
        api_server.TextRequest(
            user_text=FULL_TRADE_POUNDS,
            include_raw_response=False,
        )
    )
    assert metrics(routed)["total_weight_kg"] == 1000.0, metrics(routed)
    assert container(routed)["total_weight_kg"] == 1000.0, container(routed)
    assert_single_tiles(routed, 1000.0)


def test_existing_semantics_remain_unchanged():
    kg = process_text_request(
        "Create a full trade plan for 10 CBM ceramic tiles "
        "from India to USA using CIF. Total weight is 1200 kg. "
        "Include logistics, documents, duty, and risk."
    )
    assert metrics(kg)["total_weight_kg"] == 1200, metrics(kg)

    unknown = process_text_request(
        "Ship 10 cubic feet of tiles from India to USA."
    )
    assert metrics(unknown)["total_weight_kg"] is None, metrics(unknown)
    assert container(unknown)["total_weight_kg"] is None, container(unknown)

    multi = process_text_request(
        "Ship 2 CBM pumps weighing 500 kg, "
        "3 CBM valves weighing 300 kg and "
        "1 CBM seals weighing 50 kg from India to USA."
    )
    assert metrics(multi)["total_cbm"] == 6, metrics(multi)
    assert metrics(multi)["total_weight_kg"] == 850, metrics(multi)

    heavy = process_text_request(
        "Ship 20 CBM of steel parts weighing 40000 kg "
        "from India to USA."
    )
    assert metrics(heavy)["total_weight_kg"] == 40000, metrics(heavy)


def main():
    test_cbm_name_without_of()
    test_cbm_name_with_of_stays_correct()
    test_converted_weight_is_practical_precision()
    test_existing_semantics_remain_unchanged()

    print("PASS - CBM is not included in single-item cargo names")
    print("PASS - with-of and without-of CBM prompts produce ceramic tiles")
    print("PASS - converted pounds display as 1000.0 kg in backend and API payloads")
    print("PASS - kg, unknown-weight, multi-item and heavy cases remain unchanged")


if __name__ == "__main__":
    main()
