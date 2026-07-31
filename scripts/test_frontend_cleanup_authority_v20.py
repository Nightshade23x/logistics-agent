from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_text_request
from app.frontend_response_cleanup import (
    cleanup_frontend_response,
)
from app.text_shipment_parser import (
    parse_shipment_text,
)


FULL_TRADE_PROMPT = (
    "Create a full trade plan for 10 CBM ceramic tiles "
    "from India to USA using CIF. Total weight is 1200 kg. "
    "Include logistics, documents, duty, and risk."
)


def totals(payload):
    metrics = payload.get("logistics_metrics") or {}
    container = (
        (payload.get("logistics_visualizer") or {})
        .get("container")
        or {}
    )

    return (
        metrics.get("total_cbm"),
        metrics.get("total_weight_kg"),
        container.get("total_cbm"),
        container.get("total_weight_kg"),
    )


def test_final_backend_payload_cleanup_is_idempotent():
    backend = process_text_request(
        FULL_TRADE_PROMPT
    )

    assert totals(backend) == (
        10.0,
        1200.0,
        10.0,
        1200.0,
    ), totals(backend)

    cleaned = cleanup_frontend_response(
        deepcopy(backend),
        FULL_TRADE_PROMPT,
    )

    assert totals(cleaned) == (
        10.0,
        1200.0,
        10.0,
        1200.0,
    ), totals(cleaned)

    assert cleaned["logistics_metrics"] == (
        backend["logistics_metrics"]
    )
    assert cleaned["logistics_visualizer"] == (
        backend["logistics_visualizer"]
    )


def test_parser_does_not_create_kg_cargo_item():
    parsed = parse_shipment_text(
        FULL_TRADE_PROMPT
    )

    names = [
        str(
            item.get("name")
            or item.get("item_name")
            or ""
        ).strip().lower()
        for item in parsed.get("items", [])
        if isinstance(item, dict)
    ]

    assert "kg" not in names, parsed
    assert names == ["ceramic tiles"], parsed
    assert parsed["total_weight_kg"] == 1200, parsed

    item = parsed["items"][0]

    assert item["total_weight_kg"] == 1200, item
    assert item["weight_estimated"] is False, item
    assert (
        item["weight_source"]
        == "explicit_total_weight"
    ), item


def test_heavy_and_multi_item_totals_remain_correct():
    heavy_prompt = (
        "Ship 10 CBM ceramic tiles weighing 20000 kg "
        "from India to USA."
    )

    multi_prompt = (
        "Ship 2 CBM pumps weighing 500 kg, "
        "3 CBM valves weighing 300 kg and "
        "1 CBM seals weighing 50 kg from India to USA."
    )

    heavy = process_text_request(heavy_prompt)
    heavy_cleaned = cleanup_frontend_response(
        deepcopy(heavy),
        heavy_prompt,
    )

    multi = process_text_request(multi_prompt)
    multi_cleaned = cleanup_frontend_response(
        deepcopy(multi),
        multi_prompt,
    )

    assert totals(heavy_cleaned)[1] == 20000, (
        totals(heavy_cleaned)
    )
    assert totals(heavy_cleaned)[3] == 20000, (
        totals(heavy_cleaned)
    )

    assert totals(multi_cleaned)[0] == 6, (
        totals(multi_cleaned)
    )
    assert totals(multi_cleaned)[1] == 850, (
        totals(multi_cleaned)
    )


def test_unknown_weight_semantics_remain_correct():
    prompt = (
        "Ship 10 cubic feet of tiles "
        "from India to USA."
    )

    backend = process_text_request(prompt)
    cleaned = cleanup_frontend_response(
        deepcopy(backend),
        prompt,
    )

    assert totals(cleaned)[1] is None, (
        totals(cleaned)
    )
    assert totals(cleaned)[3] is None, (
        totals(cleaned)
    )

    assert (
        cleaned["logistics_visualizer"]
        ["fit_check"]["status"]
        == "volume_fits_payload_unverified"
    )


def main():
    test_final_backend_payload_cleanup_is_idempotent()
    test_parser_does_not_create_kg_cargo_item()
    test_heavy_and_multi_item_totals_remain_correct()
    test_unknown_weight_semantics_remain_correct()

    print(
        "PASS - finalized backend payload cleanup "
        "is idempotent"
    )
    print(
        "PASS - full trade remains 10 CBM and "
        "1200 kg through HTTP cleanup"
    )
    print(
        "PASS - parser no longer creates a "
        "synthetic kg cargo item"
    )
    print(
        "PASS - 20000 kg heavy and 850 kg "
        "multi-item totals remain unchanged"
    )
    print(
        "PASS - unknown-weight cubic-feet "
        "semantics remain unchanged"
    )


if __name__ == "__main__":
    main()
