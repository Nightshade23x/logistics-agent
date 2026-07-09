from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    env = os.environ.copy()
    env.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_compact_frontend_payload.py",
            "json",
            "data/suppliers/sample_shopping_request.json",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(result.returncode)

    payload = json.loads(result.stdout)
    visualizer = payload.get("logistics_visualizer")

    assert isinstance(visualizer, dict), "logistics_visualizer must be a dict"
    assert visualizer.get("status") == "available"
    assert visualizer.get("visualizer_type") == "container_load_visualizer"

    container = visualizer.get("container", {})
    assert container.get("selected_container") == "20ft Standard Container"
    assert container.get("utilization_percent") is not None
    assert container.get("total_cbm") == 19.41

    cargo_mix = visualizer.get("cargo_mix", [])
    assert len(cargo_mix) >= 3
    assert any(item.get("item_name") == "TVs" for item in cargo_mix)

    zone_layout = visualizer.get("zone_layout", [])
    assert len(zone_layout) >= 1

    loading_sequence = visualizer.get("loading_sequence", [])
    assert len(loading_sequence) >= 1

    validation = payload.get("backend_validation", {})
    assert validation.get("response_contract_valid") is True

    print("PASS: logistics_visualizer is available in compact frontend payload")


if __name__ == "__main__":
    main()
