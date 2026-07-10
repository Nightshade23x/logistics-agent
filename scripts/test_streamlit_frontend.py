from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    module = importlib.import_module("app.streamlit_frontend")

    payload = module.get_sample_shopping_payload()

    assert payload.get("payload_type") == "compact_frontend_payload"
    assert payload.get("detected_intent") == "shopping"
    assert payload.get("backend_validation", {}).get("response_contract_valid") is True
    assert payload.get("logistics_visualizer", {}).get("status") == "available"

    assert module.humanize("review_required") == "Review Required"
    assert module.humanize("fcl_preferred") == "FCL Preferred"
    assert module.humanize(True) == "Yes"
    assert module.humanize(False) == "No"

    print("PASS: Streamlit frontend smoke test passed")


if __name__ == "__main__":
    main()
