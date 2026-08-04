from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.backend_service import process_text_request


def number(value: Any) -> float:
    return float(value)


def section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def cargo_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    visualizer = section(payload, "logistics_visualizer")
    items = visualizer.get("cargo_mix")

    assert isinstance(items, list), visualizer

    output: dict[str, dict[str, Any]] = {}

    for item in items:
        assert isinstance(item, dict), item

        name = str(
            item.get("item_name")
            or item.get("name")
            or ""
        ).strip().lower()

        if name:
            output[name] = item

    return output


def assert_item(
    item: dict[str, Any],
    expected_cbm: float,
    expected_weight: float,
) -> None:
    assert number(item.get("total_cbm")) == expected_cbm, item
    assert number(item.get("total_weight_kg")) == expected_weight, item


def assert_totals(
    payload: dict[str, Any],
    expected_cbm: float,
    expected_weight: float,
) -> None:
    metrics = section(payload, "logistics_metrics")
    visualizer = section(payload, "logistics_visualizer")
    container = (
        visualizer.get("container")
        if isinstance(visualizer.get("container"), dict)
        else {}
    )
    handoff = section(payload, "handoff_payload")
    review = section(payload, "logistics_quality_review")

    for label, values in (
        ("metrics", metrics),
        ("container", container),
        ("handoff", handoff),
        ("review", review),
    ):
        assert number(values.get("total_cbm")) == expected_cbm, (
            label,
            values,
        )
        assert number(values.get("total_weight_kg")) == expected_weight, (
            label,
            values,
        )


def test_three_item_prompt() -> None:
    prompt = (
        "Ship 2 CBM pumps weighing 500 kg, "
        "3 CBM valves weighing 300 kg and "
        "1 CBM seals weighing 50 kg from India to USA."
    )

    payload = process_text_request(prompt)
    items = cargo_map(payload)

    assert set(items) == {
        "pumps",
        "valves",
        "seals",
    }, items

    assert_item(items["pumps"], 2, 500)
    assert_item(items["valves"], 3, 300)
    assert_item(items["seals"], 1, 50)
    assert_totals(payload, 6, 850)

    visualizer = section(payload, "logistics_visualizer")
    display = (
        visualizer.get("display_metrics")
        if isinstance(visualizer.get("display_metrics"), dict)
        else {}
    )

    assert number(display.get("loaded_cbm")) == 6, display
    assert abs(number(display.get("utilization_percent")) - 18.07) <= 0.01, display


def test_two_item_prompt() -> None:
    prompt = (
        "Ship 10 CBM ceramic tiles weighing 1200 kg and "
        "4 CBM pillows weighing 350 kg from India to USA."
    )

    payload = process_text_request(prompt)
    items = cargo_map(payload)

    assert set(items) == {
        "ceramic tiles",
        "pillows",
    }, items

    assert_item(items["ceramic tiles"], 10, 1200)
    assert_item(items["pillows"], 4, 350)
    assert_totals(payload, 14, 1550)


def test_payload_limit_prompt() -> None:
    prompt = (
        "Ship 20 CBM of steel parts weighing 40000 kg "
        "from India to USA."
    )

    payload = process_text_request(prompt)
    assert_totals(payload, 20, 40000)

    constraint = section(payload, "payload_constraint")
    assert constraint.get("status") == "blocked", constraint


def main() -> None:
    test_three_item_prompt()
    print("PASS - three separate cargo rows, 6 CBM and 850 kg")

    test_two_item_prompt()
    print("PASS - two-item case remains 14 CBM and 1550 kg")

    test_payload_limit_prompt()
    print("PASS - steel payload-limit case remains blocked")

    print("")
    print("ALL CONTAINER MULTI-ITEM BACKEND TESTS PASSED")


if __name__ == "__main__":
    main()
