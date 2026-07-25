
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend_service import process_text_request


OUT_DIR = Path("demo_outputs/json_regression_v11")
OUT_DIR.mkdir(parents=True, exist_ok=True)


CASES = [
    {
        "name": "q1",
        "prompt": "What is the HS code, import duty rate and FTA status for ceramic tiles exported from India to the USA?",
    },
    {
        "name": "q2",
        "prompt": "Ship 1.2 CBM of lithium batteries weighing 1000 kg from India to Germany. The cargo is hazardous and non-stackable.",
    },
    {
        "name": "q3",
        "prompt": "Ship 10 pallets of ceramic tiles from India to USA using CIF. Total cargo is 10 CBM and 1200 kg.",
    },
    {
        "name": "q4",
        "prompt": "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, 5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB.",
    },
    {
        "name": "q5",
        "prompt": "Finance Agent: calculate landed cost for ceramic tiles from India to USA using CIF. Procurement value 12000 USD, freight quote 3500 USD, insurance 600 USD, duty 8 percent, import tax 6 percent, customs brokerage 400 USD, local delivery 800 USD. Total cargo is 10 CBM and 1200 kg.",
    },
    {
        "name": "q6",
        "prompt": "What documents are needed to ship hazardous chemicals from India to Germany using CIF? Include dangerous goods declaration, MSDS, insurance, and compliance readiness.",
    },
]


def near(value: Any, expected: float, tolerance: float = 0.05) -> bool:
    try:
        return abs(float(value) - float(expected)) <= tolerance
    except Exception:
        return False


def get_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("logistics_metrics")
    return metrics if isinstance(metrics, dict) else {}


def get_agents(payload: dict[str, Any]) -> list[str]:
    agents = payload.get("agents_called")
    return agents if isinstance(agents, list) else []


def get_visualizer(payload: dict[str, Any]) -> dict[str, Any]:
    visualizer = payload.get("logistics_visualizer")
    return visualizer if isinstance(visualizer, dict) else {}


def get_fit_status(payload: dict[str, Any]) -> str | None:
    visualizer = get_visualizer(payload)
    fit = visualizer.get("fit_check")
    if isinstance(fit, dict):
        return fit.get("status")
    return None


def get_landed_cost(payload: dict[str, Any]) -> float | None:
    landed = payload.get("landed_cost_advice")
    if isinstance(landed, dict):
        value = landed.get("estimated_landed_cost_usd")
        if value is not None:
            try:
                return float(value)
            except Exception:
                return None
    return None


def get_doc_item_count(payload: dict[str, Any]) -> int:
    advice = payload.get("document_requirements_advice")
    if isinstance(advice, dict):
        count = advice.get("item_count")
        try:
            return int(count)
        except Exception:
            return 0
    return 0


def find_cargo_item(payload: dict[str, Any], *tokens: str) -> dict[str, Any] | None:
    visualizer = get_visualizer(payload)
    cargo_mix = visualizer.get("cargo_mix")
    if not isinstance(cargo_mix, list):
        return None

    wanted = [token.lower() for token in tokens]

    for item in cargo_mix:
        if not isinstance(item, dict):
            continue

        name = str(item.get("item_name") or item.get("name") or "").lower()
        if all(token in name for token in wanted):
            return item

    return None


def has_text(payload: Any, text: str) -> bool:
    return text.lower() in json.dumps(payload, ensure_ascii=False, default=str).lower()


def print_case(name: str, payload: dict[str, Any], ok: bool, problems: list[str]) -> None:
    metrics = get_metrics(payload)
    visualizer = get_visualizer(payload)
    landed = get_landed_cost(payload)

    print("")
    print("=" * 88)
    print(name.upper())
    print("=" * 88)
    print("agents:", get_agents(payload))
    print("metrics:", metrics)
    print("visualizer:", visualizer.get("status", "unavailable"))
    print("fit:", get_fit_status(payload) or "unavailable")
    print("landed_cost:", landed)
    print("contract_valid:", isinstance(payload, dict) and "status" in payload and "agents_called" in payload)
    print("saved:", OUT_DIR / f"{name}.json")
    print("PASS" if ok else "FAIL")

    for problem in problems:
        print("-", problem)


def validate_q1(payload: dict[str, Any]) -> list[str]:
    problems = []
    agents = get_agents(payload)

    if agents != ["trader_agent"]:
        problems.append(f"Q1 should call trader_agent only: {agents}")

    if get_visualizer(payload).get("status") not in [None, "unavailable"]:
        problems.append("Q1 should not create a logistics visualizer")

    if has_text(payload, "ceramic tiles exported from India to the USA"):
        problems.append("Q1 still leaks route phrase into product name")

    return problems


def validate_q2(payload: dict[str, Any]) -> list[str]:
    problems = []
    metrics = get_metrics(payload)
    item = find_cargo_item(payload, "lithium") or find_cargo_item(payload, "batter")

    if not near(metrics.get("total_cbm"), 1.2):
        problems.append(f"Q2 CBM incorrect: {metrics}")

    if not near(metrics.get("total_weight_kg"), 1000):
        problems.append(f"Q2 weight incorrect: {metrics}")

    if metrics.get("risk_level") not in ["high", "critical"]:
        problems.append(f"Q2 should be high/critical risk: {metrics}")

    if get_visualizer(payload).get("status") != "available":
        problems.append("Q2 visualizer should be available")

    if not isinstance(item, dict):
        problems.append("Q2 lithium battery cargo item missing")
    else:
        tags = item.get("category_tags") or []
        if "hazardous" not in tags or "lithium_battery" not in tags:
            problems.append(f"Q2 lithium hazard tags missing: {item}")

        if item.get("stackable") is not False and "non_stackable" not in tags:
            problems.append(f"Q2 stackability incorrect: {item}")

    return problems


def validate_q3(payload: dict[str, Any]) -> list[str]:
    problems = []
    metrics = get_metrics(payload)

    if not near(metrics.get("total_cbm"), 10):
        problems.append(f"Q3 CBM incorrect: {metrics}")

    if not near(metrics.get("total_weight_kg"), 1200):
        problems.append(f"Q3 weight incorrect: {metrics}")

    if get_visualizer(payload).get("status") != "available":
        problems.append("Q3 visualizer should be available")

    if get_landed_cost(payload) is not None:
        problems.append("Q3 should not calculate landed cost without cost inputs")

    return problems


def validate_q4(payload: dict[str, Any]) -> list[str]:
    problems = []
    metrics = get_metrics(payload)
    visualizer = get_visualizer(payload)
    ceramic = find_cargo_item(payload, "ceramic", "tile")

    if not near(metrics.get("total_cbm"), 22.1):
        problems.append(f"Q4 total_cbm should be 22.1: {metrics}")

    if not near(metrics.get("total_weight_kg"), 437):
        problems.append(f"Q4 total_weight_kg should be 437: {metrics}")

    if visualizer.get("status") != "available":
        problems.append("Q4 visualizer should be available")

    cargo_mix = visualizer.get("cargo_mix")
    if not isinstance(cargo_mix, list) or len(cargo_mix) < 4:
        problems.append("Q4 cargo_mix should include ceramic tiles, pillows, mattresses, and glass bottles")

    if not isinstance(ceramic, dict):
        problems.append("Q4 ceramic tile item missing")
    else:
        if ceramic.get("aggregate_volume_only") is not True:
            problems.append(f"Q4 aggregate marker missing: {ceramic}")

        tile_weight = ceramic.get("total_weight_kg")
        if not near(tile_weight, 250):
            problems.append(f"Q4 ceramic fallback weight should be 250 kg: {ceramic}")

        if ceramic.get("weight_estimated") is not True:
            problems.append(f"Q4 ceramic fallback should be marked estimated: {ceramic}")

    if get_landed_cost(payload) is not None:
        problems.append("Q4 should not calculate landed cost without full cost inputs")

    return problems


def validate_q5(payload: dict[str, Any]) -> list[str]:
    problems = []
    agents = get_agents(payload)
    landed = get_landed_cost(payload)

    if "finance_agent" not in agents:
        problems.append(f"Q5 should call finance_agent: {agents}")

    if not near(landed, 19631.28):
        problems.append(f"Q5 landed cost incorrect: {landed}")

    return problems


def validate_q6(payload: dict[str, Any]) -> list[str]:
    problems = []
    agents = get_agents(payload)
    doc_count = get_doc_item_count(payload)

    if "document_ai_agent" not in agents:
        problems.append(f"Q6 should call document_ai_agent: {agents}")

    if "compliance_agent" not in agents:
        problems.append(f"Q6 should call compliance_agent: {agents}")

    if doc_count < 1:
        problems.append(f"Q6 doc item count should be at least 1: {doc_count}")

    if not (has_text(payload, "MSDS") or has_text(payload, "Dangerous Goods Declaration")):
        problems.append("Q6 should include MSDS or Dangerous Goods Declaration")

    return problems


VALIDATORS = {
    "q1": validate_q1,
    "q2": validate_q2,
    "q3": validate_q3,
    "q4": validate_q4,
    "q5": validate_q5,
    "q6": validate_q6,
}


def main() -> int:
    all_problems: list[str] = []

    for case in CASES:
        name = case["name"]
        prompt = case["prompt"]

        payload = process_text_request(prompt)
        path = OUT_DIR / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        validator = VALIDATORS[name]
        problems = validator(payload)

        print_case(name, payload, not problems, problems)

        for problem in problems:
            all_problems.append(problem)

    print("")
    print("=" * 88)
    print("FINAL RESULT")
    print("=" * 88)

    if all_problems:
        print("FAILED CHECKS:")
        for problem in all_problems:
            print("-", problem)
        return 1

    print("ALL SIX JSON REGRESSION CASES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
