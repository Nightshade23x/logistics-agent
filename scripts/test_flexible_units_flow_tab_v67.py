from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["LLM_INTERPRETER_MODE"] = "off"

from fastapi.testclient import TestClient
from api_server import app

os.environ["LLM_INTERPRETER_MODE"] = "off"


def require(condition: bool, message: str, value=None) -> None:
    if condition:
        return

    suffix = (
        ""
        if value is None
        else "\n"
        + json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )
    raise AssertionError(message + suffix)


def post(client: TestClient, prompt: str) -> dict:
    os.environ["LLM_INTERPRETER_MODE"] = "off"

    response = client.post(
        "/api/request/text",
        json={
            "user_text": prompt,
            "include_raw_response": False,
        },
    )

    require(
        response.status_code == 200,
        f"Request returned HTTP {response.status_code}",
        response.text[:4000],
    )

    payload = response.json()
    require(
        isinstance(payload, dict),
        "Response is not an object",
        payload,
    )
    return payload


wizard = (
    ROOT
    / "frontend/src/components/GuidedShipmentWizard.jsx"
).read_text(encoding="utf-8")
app_text = (
    ROOT / "frontend/src/App.jsx"
).read_text(encoding="utf-8")
sidebar = (
    ROOT / "frontend/src/components/Sidebar.jsx"
).read_text(encoding="utf-8")
answer_card = (
    ROOT / "frontend/src/components/AnswerCard.jsx"
).read_text(encoding="utf-8")
process_page = (
    ROOT / "frontend/src/pages/ProcessFlow.jsx"
).read_text(encoding="utf-8")
container_page = (
    ROOT / "frontend/src/pages/ContainerPlanning.jsx"
).read_text(encoding="utf-8")
cleanup = (
    ROOT / "app/frontend_response_cleanup.py"
).read_text(encoding="utf-8")
backend = (
    ROOT / "app/backend_service.py"
).read_text(encoding="utf-8")

for required in (
    'option value="volume"',
    'option value="cbm"',
    'option value="litres"',
    'option value="millilitres"',
    'option value="cubic_feet"',
    'option value="cubic_inches"',
    'option value="custom">Other — enter your own',
    'wizard-customPackageType',
    'wizard-customDimensionUnit',
    'wizard-customVolumeUnit',
    'wizard-customWeightUnit',
    'wizard-customCurrency',
    'metresPerCustomDimensionUnit',
    'cbmPerCustomVolumeUnit',
    'kgPerCustomWeightUnit',
    'DETERMINISTIC_DIRECT_VOLUME_V67',
):
    require(
        required in wizard,
        f"Guided form is missing: {required}",
    )

for currency in (
    "USD",
    "EUR",
    "GBP",
    "ZMW",
    "INR",
):
    require(
        f'<option value="{currency}">{currency}</option>'
        in wizard,
        f"Currency dropdown is missing {currency}",
    )

require(
    'path="/process-flow"' in app_text,
    "Process Flow route is missing",
)
require(
    'to: "/process-flow"' in sidebar,
    "Process Flow sidebar item is missing",
)
require(
    "AnswerFlow" not in answer_card,
    "Flowchart is still embedded in the answer card",
)
require(
    "<AnswerFlow result={result} />" in process_page,
    "Process Flow page is not connected to the active result",
)
require(
    "displayWeightValue" in container_page
    and "displayWeightUnit" in container_page,
    "Container Planning weight display is not unit-aware",
)
require(
    "displayVolumeValue" in container_page
    and "displayVolumeUnit" in container_page,
    "Container Planning volume display is not unit-aware",
)
require(
    "def _v67_sync_weight" in cleanup
    and "def _v67_sync_volume" in cleanup,
    "V67 display-unit synchronisation is missing",
)
require(
    "ORIGINAL_DISPLAY_UNITS_FINALIZATION_V68"
    in backend,
    "The final original-text display-unit wrapper is missing",
)

prompts = {
    "lbs": (
        "Ship 10 crates of ceramic tiles from India to Germany "
        "using CIF. Each crate is 1.2 m x 1.0 m x 0.8 m and "
        "weighs 250 lbs. The cargo is fragile and stackable."
    ),
    "llbs": (
        "Ship 10 crates of ceramic tiles from India to Germany "
        "using CIF. Each crate is 1.2 m x 1.0 m x 0.8 m and "
        "weighs 250 llbs. The cargo is fragile and stackable."
    ),
    "litres": (
        "Ship 10 crates of liquid product from India to Germany "
        "using CIF. Each crate has packed volume of 100 litres. "
        "Original package volume: 100 litres. "
        "The total shipment volume is 1 CBM for calculation. "
        "1 CBM of liquid product weighing 1133.980925 kg total. "
        "Each crate weighs 250 lb."
    ),
}

with TestClient(app) as client:
    payloads = {
        name: post(client, prompt)
        for name, prompt in prompts.items()
    }

for name in ("lbs", "llbs"):
    payload = payloads[name]
    display = (
        (payload.get("display_measurements") or {}).get(
            "weight"
        )
        or {}
    )
    metrics = payload.get("logistics_metrics") or {}
    metadata = payload.get("request_metadata") or {}

    require(
        display.get("display_unit") == "lb",
        f"{name}: display unit was not preserved as lb",
        {
            "display_measurements": payload.get(
                "display_measurements"
            ),
            "metrics": metrics,
            "metadata": metadata,
        },
    )
    require(
        abs(
            float(display.get("total_weight") or 0)
            - 2500
        )
        < 0.001,
        f"{name}: display total should be 2500 lb",
        display,
    )
    require(
        abs(
            float(metrics.get("total_weight_kg") or 0)
            - 1133.980925
        )
        < 0.1,
        f"{name}: internal kilogram total is incorrect",
        metrics,
    )
    require(
        (
            metadata.get(
                "original_display_units_finalization_v68"
            )
            or {}
        ).get("status")
        == "applied",
        f"{name}: final original-text wrapper did not run",
        metadata,
    )

volume_payload = payloads["litres"]
volume = (
    (volume_payload.get("display_measurements") or {}).get(
        "volume"
    )
    or {}
)
weight = (
    (volume_payload.get("display_measurements") or {}).get(
        "weight"
    )
    or {}
)
metrics = volume_payload.get("logistics_metrics") or {}
visualizer = (
    volume_payload.get("logistics_visualizer") or {}
)
container = visualizer.get("container") or {}

require(
    volume.get("display_unit") == "L",
    "Litres were not preserved for display",
    volume,
)
require(
    abs(float(volume.get("total_volume") or 0) - 1000)
    < 0.001,
    "Total display volume should be 1000 L",
    volume,
)
require(
    weight.get("display_unit") == "lb",
    "Direct-volume shipment did not preserve pounds",
    weight,
)
require(
    abs(float(metrics.get("total_cbm") or 0) - 1)
    < 0.001,
    "Internal total volume should be 1 CBM",
    metrics,
)
require(
    abs(float(container.get("total_cbm") or 0) - 1)
    < 0.001,
    "Container total should remain 1 CBM",
    container,
)

print(
    "PASS - guided form supports standard and custom package, "
    "dimension, volume, weight and currency values"
)
print(
    "PASS - Process Flow has its own route and sidebar tab"
)
print(
    "PASS - lbs and llbs remain pounds in the final API payload "
    "while kilograms remain internal"
)
print(
    "PASS - litres remain litres while CBM remains internal"
)
print(
    "PASS - original user units survive every backend and "
    "frontend cleanup wrapper"
)
print("All V68 final display-unit regressions passed.")
