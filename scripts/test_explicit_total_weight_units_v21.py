from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api_server

from app.backend_service import process_text_request
from app.frontend_response_cleanup import cleanup_frontend_response


LB_PROMPT = (
    "Create a full trade plan for 10 CBM ceramic tiles "
    "from India to USA using CIF. "
    "Total weight is 2204.62 lb. "
    "Include logistics, documents, duty, and risk."
)


def totals(payload):
    metrics = payload.get(
        "logistics_metrics"
    ) or {}

    container = (
        (
            payload.get(
                "logistics_visualizer"
            )
            or {}
        ).get("container")
        or {}
    )

    return (
        metrics.get("total_cbm"),
        metrics.get("total_weight_kg"),
        container.get("total_cbm"),
        container.get("total_weight_kg"),
    )


def near_1000(value):
    assert value is not None, value
    assert abs(float(value) - 1000) < 0.01, value


def test_pounds_full_trade():
    backend = process_text_request(
        LB_PROMPT
    )

    values = totals(backend)

    assert values[0] == 10, values
    assert values[2] == 10, values

    near_1000(values[1])
    near_1000(values[3])

    visualizer = backend[
        "logistics_visualizer"
    ]

    cargo = visualizer.get(
        "cargo_mix"
    ) or []

    assert len(cargo) == 1, cargo
    assert (
        cargo[0].get("item_name")
        == "ceramic tiles"
    ), cargo

    near_1000(
        cargo[0].get(
            "total_weight_kg"
        )
    )

    fit_check = (
        visualizer.get("fit_check")
        or {}
    )

    assert (
        fit_check.get(
            "selected_container_checked"
        )
        == visualizer["container"].get(
            "selected_container"
        )
    ), fit_check

    cleaned = cleanup_frontend_response(
        deepcopy(backend),
        LB_PROMPT,
    )

    near_1000(totals(cleaned)[1])
    near_1000(totals(cleaned)[3])

    routed = api_server.request_text(
        api_server.TextRequest(
            user_text=LB_PROMPT,
            include_raw_response=False,
        )
    )

    near_1000(totals(routed)[1])
    near_1000(totals(routed)[3])


def test_existing_cases():
    kg = process_text_request(
        "Create a full trade plan for 10 CBM ceramic tiles "
        "from India to USA using CIF. "
        "Total weight is 1200 kg. "
        "Include logistics, documents, duty, and risk."
    )

    assert totals(kg)[1] == 1200

    unknown = process_text_request(
        "Ship 10 cubic feet of tiles "
        "from India to USA."
    )

    assert totals(unknown)[1] is None
    assert totals(unknown)[3] is None

    multi = process_text_request(
        "Ship 2 CBM pumps weighing 500 kg, "
        "3 CBM valves weighing 300 kg and "
        "1 CBM seals weighing 50 kg "
        "from India to USA."
    )

    assert totals(multi)[1] == 850

    heavy = process_text_request(
        "Ship 20 CBM of steel parts "
        "weighing 40000 kg "
        "from India to USA."
    )

    assert totals(heavy)[1] == 40000


if __name__ == "__main__":
    test_pounds_full_trade()
    test_existing_cases()

    print(
        "PASS - pounds remain converted "
        "through backend and HTTP cleanup"
    )
    print(
        "PASS - cargo and fit-check fields "
        "are synchronized"
    )
    print(
        "PASS - kg, unknown-weight, "
        "multi-item and heavy cases remain correct"
    )
