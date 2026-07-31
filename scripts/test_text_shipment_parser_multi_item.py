from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.text_shipment_parser import parse_shipment_text


def number(value):
    return float(value)


def item_map(payload):
    items = payload.get("items")

    assert isinstance(items, list), payload

    result = {}

    for item in items:
        assert isinstance(item, dict), item

        name = str(
            item.get("item_name")
            or item.get("name")
            or ""
        ).strip().lower()

        if name:
            result[name] = item

    return result


def assert_item(item, cbm, weight):
    assert number(item.get("total_cbm")) == cbm, item
    assert number(item.get("unit_cbm")) == cbm, item
    assert number(item.get("total_weight_kg")) == weight, item
    assert number(item.get("unit_weight_kg")) == weight, item
    assert item.get("aggregate_volume_only") is True, item
    assert item.get("dimensions_are_aggregate") is True, item
    assert item.get("weight_estimated") is False, item
    assert item.get("weight_source") == "explicit_user_item_weight", item


def test_exact_two_item_prompt():
    prompt = (
        "Ship 10 CBM ceramic tiles weighing 1200 kg and "
        "4 CBM pillows weighing 350 kg from India to USA."
    )

    payload = parse_shipment_text(prompt)
    items = item_map(payload)

    assert set(items) == {"ceramic tiles", "pillows"}, items

    assert_item(items["ceramic tiles"], 10, 1200)
    assert_item(items["pillows"], 4, 350)

    assert number(payload.get("total_cbm")) == 14, payload
    assert number(payload.get("total_weight_kg")) == 1550, payload


def test_comma_and_plus_variant():
    prompt = (
        "Ship 10 CBM of ceramic tiles weighing 1,200 kg plus "
        "4 CBM of pillows weighing 350 kg from India to USA."
    )

    payload = parse_shipment_text(prompt)
    items = item_map(payload)

    assert set(items) == {"ceramic tiles", "pillows"}, items

    assert_item(items["ceramic tiles"], 10, 1200)
    assert_item(items["pillows"], 4, 350)

    assert number(payload.get("total_cbm")) == 14, payload
    assert number(payload.get("total_weight_kg")) == 1550, payload


def test_three_item_prompt():
    prompt = (
        "Ship 2 CBM pumps weighing 500 kg, "
        "3 CBM valves weighing 300 kg and "
        "1 CBM seals weighing 50 kg from India to USA."
    )

    payload = parse_shipment_text(prompt)
    items = item_map(payload)

    assert set(items) == {"pumps", "valves", "seals"}, items

    assert_item(items["pumps"], 2, 500)
    assert_item(items["valves"], 3, 300)
    assert_item(items["seals"], 1, 50)

    assert number(payload.get("total_cbm")) == 6, payload
    assert number(payload.get("total_weight_kg")) == 850, payload


def test_single_item_behavior_remains_supported():
    prompt = (
        "Ship 20 CBM of steel parts weighing 40000 kg "
        "from India to USA."
    )

    payload = parse_shipment_text(prompt)

    assert number(payload.get("total_cbm")) == 20, payload
    assert number(payload.get("total_weight_kg")) == 40000, payload


def main():
    test_exact_two_item_prompt()
    print("PASS - exact two-item CBM/weight clauses")

    test_comma_and_plus_variant()
    print("PASS - comma and plus variant")

    test_three_item_prompt()
    print("PASS - three explicit item clauses")

    test_single_item_behavior_remains_supported()
    print("PASS - single-item parser behavior preserved")

    print("")
    print("ALL MULTI-ITEM PARSER REGRESSION CHECKS PASSED")


if __name__ == "__main__":
    main()
