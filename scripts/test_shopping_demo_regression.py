from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str], env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    output = result.stdout + "\n" + result.stderr

    if result.returncode != 0:
        print(output)
        raise SystemExit(result.returncode)

    return result.stdout


def find_ui_section(payload: dict, section_id: str) -> dict:
    for section in payload.get("ui_sections", []):
        if isinstance(section, dict) and section.get("section_id") == section_id:
            return section

    raise AssertionError(f"Missing ui section: {section_id}")


def main() -> None:
    unit_tests = [
        "scripts/test_procurement_advisor.py",
        "scripts/test_shopping_agent.py",
        "scripts/test_shopping_quality_review.py",
    ]

    for test_script in unit_tests:
        output = run_command([sys.executable, test_script])
        print(output.strip())

    env = os.environ.copy()
    env.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    compact_output = run_command(
        [
            sys.executable,
            "scripts/run_compact_frontend_payload.py",
            "json",
            "data/suppliers/sample_shopping_request.json",
        ],
        env=env,
    )

    payload = json.loads(compact_output)

    assert payload.get("detected_intent") == "shopping"
    assert payload.get("status") == "review_required"
    assert "shopping_agent" in payload.get("agents_called", [])

    procurement_section = find_ui_section(payload, "procurement")

    assert procurement_section.get("status") == "clear"

    metrics = procurement_section.get("metrics", {})

    assert metrics.get("selected_items_count") == 3
    assert metrics.get("supplier_options_count") == 9
    assert metrics.get("estimated_total_procurement_cost_usd") == 12730.0
    assert metrics.get("supplier_countries") == ["india"]

    bullets = procurement_section.get("bullets", [])
    actions = procurement_section.get("actions", [])

    assert isinstance(bullets, list)
    assert isinstance(actions, list)

    expected_bullet_fragments = [
        "single-country sourcing risk",
        "shortlisted suppliers",
        "estimated total procurement cost 12730.0 USD",
        "payment terms",
        "packaging standard",
        "proforma invoice",
    ]

    joined_bullets = " ".join(str(item) for item in bullets)

    for fragment in expected_bullet_fragments:
        assert fragment in joined_bullets, (
            f"Missing procurement guidance fragment: {fragment}"
        )

    executive_summary = payload.get("executive_summary", {})
    shipment_snapshot = executive_summary.get("shipment_snapshot", {})

    assert shipment_snapshot.get("estimated_procurement_cost_usd") == 12730.0
    assert shipment_snapshot.get("origin_country") == "India"
    assert shipment_snapshot.get("destination_country") == "USA"

    print("PASS: shopping/procurement demo regression checks passed")


if __name__ == "__main__":
    main()
