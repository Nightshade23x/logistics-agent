
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
    # EXTENDED_LOGISTICS_REGRESSION_CASES_2026
    {
        "name": "q7",
        "prompt": (
            "Ship 8 pallets of glass jars from India to USA. "
            "Each pallet is 1.2 m x 1.0 m x 1.5 m and weighs 180 kg. "
            "The glass jars are fragile."
        ),
    },
    {
        "name": "q8",
        "prompt": (
            "Ship 10 CBM ceramic tiles weighing 1200 kg "
            "and 4 CBM pillows weighing 350 kg "
            "from India to USA."
        ),
    },
    {
        "name": "q9",
        "prompt": (
            "Ship 20 CBM of steel parts weighing 40000 kg "
            "from India to USA."
        ),
    },
    {
        "name": "q10",
        "prompt": (
            "Create a full trade plan for 10 CBM ceramic tiles "
            "from India to USA using CIF. "
            "Total weight is 1200 kg. "
            "Include logistics, documents, duty, and risk."
        ),
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


def validate_q7(payload: dict[str, Any]) -> list[str]:
    problems = []

    metrics = get_metrics(payload)
    visualizer = get_visualizer(payload)

    if not near(metrics.get("total_cbm"), 14.4):
        problems.append(
            f"Q7 total_cbm should be 14.4: {metrics}"
        )

    if not near(metrics.get("total_weight_kg"), 1440):
        problems.append(
            f"Q7 total_weight_kg should be 1440: {metrics}"
        )

    if visualizer.get("status") != "available":
        problems.append(
            "Q7 visualizer should be available"
        )

    display = visualizer.get("display_metrics")

    if not isinstance(display, dict):
        problems.append(
            "Q7 display_metrics missing"
        )
    else:
        if not near(
            display.get("loaded_cbm"),
            14.4,
        ):
            problems.append(
                f"Q7 loaded_cbm should be 14.4: {display}"
            )

        if not near(
            display.get("utilization_percent"),
            43.37,
            tolerance=0.10,
        ):
            problems.append(
                f"Q7 utilization should be about 43.37: {display}"
            )

    container = visualizer.get("container")

    if isinstance(container, dict):
        if not near(
            container.get("total_cbm"),
            14.4,
        ):
            problems.append(
                f"Q7 container CBM inconsistent: {container}"
            )

        if not near(
            container.get("total_weight_kg"),
            1440,
        ):
            problems.append(
                f"Q7 container weight inconsistent: {container}"
            )

    answer = str(
        payload.get("display_answer")
        or payload.get("frontend_answer")
        or ""
    )

    if "14.4" not in answer:
        problems.append(
            "Q7 displayed answer should contain 14.4 CBM"
        )

    if "1440" not in answer:
        problems.append(
            "Q7 displayed answer should contain 1440 kg"
        )

    return problems


def validate_q8(payload: dict[str, Any]) -> list[str]:
    problems = []

    metrics = get_metrics(payload)
    visualizer = get_visualizer(payload)

    if not near(metrics.get("total_cbm"), 14):
        problems.append(
            f"Q8 total_cbm should be 14: {metrics}"
        )

    if not near(metrics.get("total_weight_kg"), 1550):
        problems.append(
            f"Q8 total_weight_kg should be 1550: {metrics}"
        )

    ceramic = find_cargo_item(
        payload,
        "ceramic",
        "tile",
    )

    pillows = find_cargo_item(
        payload,
        "pillow",
    )

    if not isinstance(ceramic, dict):
        problems.append(
            "Q8 ceramic tiles item missing"
        )
    else:
        if not near(
            ceramic.get("total_cbm"),
            10,
        ):
            problems.append(
                f"Q8 ceramic CBM should be 10: {ceramic}"
            )

        if not near(
            ceramic.get("total_weight_kg"),
            1200,
        ):
            problems.append(
                f"Q8 ceramic weight should be 1200: {ceramic}"
            )

        if ceramic.get("weight_estimated") is True:
            problems.append(
                "Q8 explicit ceramic weight must not be estimated"
            )

    if not isinstance(pillows, dict):
        problems.append(
            "Q8 pillows item missing"
        )
    else:
        if not near(
            pillows.get("total_cbm"),
            4,
        ):
            problems.append(
                f"Q8 pillows CBM should be 4: {pillows}"
            )

        if not near(
            pillows.get("total_weight_kg"),
            350,
        ):
            problems.append(
                f"Q8 pillows weight should be 350: {pillows}"
            )

    display = visualizer.get("display_metrics")

    if not isinstance(display, dict):
        problems.append(
            "Q8 display_metrics missing"
        )
    else:
        if not near(
            display.get("loaded_cbm"),
            14,
        ):
            problems.append(
                f"Q8 loaded_cbm should be 14: {display}"
            )

        if not near(
            display.get("utilization_percent"),
            42.17,
            tolerance=0.10,
        ):
            problems.append(
                f"Q8 utilization should be about 42.17: {display}"
            )

    questions = []

    clarification = payload.get(
        "clarification_questions"
    )

    if isinstance(clarification, list):
        questions.extend(clarification)

    action_plan = payload.get(
        "action_plan"
    )

    if isinstance(action_plan, dict):
        values = action_plan.get(
            "user_questions"
        )

        if isinstance(values, list):
            questions.extend(values)

    for question in questions:
        lower = str(question).lower()

        if (
            "cbm" in lower
            and (
                "dimension" in lower
                or "packed" in lower
            )
        ):
            problems.append(
                f"Q8 false CBM clarification remains: {question}"
            )

    return problems


def validate_q9(payload: dict[str, Any]) -> list[str]:
    problems = []

    metrics = get_metrics(payload)

    if not near(metrics.get("total_cbm"), 20):
        problems.append(
            f"Q9 total_cbm should be 20: {metrics}"
        )

    if not near(metrics.get("total_weight_kg"), 40000):
        problems.append(
            f"Q9 total_weight_kg should be 40000: {metrics}"
        )

    expected = (
        "Multiple containers or specialist "
        "heavy-cargo planning required"
    )

    if metrics.get("recommended_container") != expected:
        problems.append(
            f"Q9 wrong recommendation: {metrics}"
        )

    if (
        metrics.get("readiness_status")
        != "not_ready_payload_limit_exceeded"
    ):
        problems.append(
            f"Q9 readiness should be payload-limit exceeded: {metrics}"
        )

    if get_fit_status(payload) != "payload_limit_exceeded":
        problems.append(
            f"Q9 fit status incorrect: {get_fit_status(payload)}"
        )

    constraint = payload.get(
        "payload_constraint"
    )

    if not isinstance(constraint, dict):
        problems.append(
            "Q9 payload_constraint missing"
        )
    else:
        if constraint.get("status") != "blocked":
            problems.append(
                f"Q9 constraint should be blocked: {constraint}"
            )

        if not near(
            constraint.get("shipment_weight_kg"),
            40000,
        ):
            problems.append(
                f"Q9 shipment weight incorrect: {constraint}"
            )

        if not near(
            constraint.get("reference_payload_kg"),
            28200,
        ):
            problems.append(
                f"Q9 reference payload incorrect: {constraint}"
            )

        if not near(
            constraint.get("payload_overage_kg"),
            11800,
        ):
            problems.append(
                f"Q9 overage incorrect: {constraint}"
            )

    answer = str(
        payload.get("display_answer")
        or ""
    )

    if (
        "not feasible as a single standard-container load"
        not in answer.lower()
    ):
        problems.append(
            "Q9 should state single-container infeasibility"
        )

    if (
        "Compare FCL quotes for 20ft, 40ft"
        in answer
    ):
        problems.append(
            "Q9 stale normal-FCL recommendation remains"
        )

    questions = []

    clarification = payload.get(
        "clarification_questions"
    )

    if isinstance(clarification, list):
        questions.extend(clarification)

    action_plan = payload.get(
        "action_plan"
    )

    if isinstance(action_plan, dict):
        values = action_plan.get(
            "user_questions"
        )

        if isinstance(values, list):
            questions.extend(values)

    for question in questions:
        lower = str(question).lower()

        if (
            "cbm" in lower
            and (
                "dimension" in lower
                or "packed" in lower
            )
        ):
            problems.append(
                f"Q9 false CBM clarification remains: {question}"
            )

    review = payload.get(
        "logistics_quality_review"
    )

    if isinstance(review, dict):
        if review.get("status") != "blocked":
            problems.append(
                f"Q9 logistics review should be blocked: {review}"
            )

    return problems


def validate_q10(payload: dict[str, Any]) -> list[str]:
    problems = []

    metrics = get_metrics(payload)
    visualizer = get_visualizer(payload)

    if not near(metrics.get("total_cbm"), 10):
        problems.append(
            f"Q10 total_cbm should be 10: {metrics}"
        )

    if not near(metrics.get("total_weight_kg"), 1200):
        problems.append(
            f"Q10 total_weight_kg should be 1200: {metrics}"
        )

    container = visualizer.get(
        "container"
    )

    if isinstance(container, dict):
        if not near(
            container.get("total_weight_kg"),
            1200,
        ):
            problems.append(
                f"Q10 visualizer weight should be 1200: {container}"
            )

    display_answer = str(
        payload.get("display_answer")
        or ""
    )

    frontend_answer = str(
        payload.get("frontend_answer")
        or ""
    )

    final_answer = payload.get(
        "final_answer"
    )

    final_text = ""

    if isinstance(final_answer, dict):
        final_text = str(
            final_answer.get("answer_text")
            or ""
        )

    if "First-pass verdict:" not in display_answer:
        problems.append(
            "Q10 rich full-trade answer missing"
        )

    if frontend_answer != display_answer:
        problems.append(
            "Q10 frontend_answer does not match display_answer"
        )

    if final_text != display_answer:
        problems.append(
            "Q10 final answer text does not match display_answer"
        )

    if "ceramic tiles" not in display_answer.lower():
        problems.append(
            "Q10 answer should mention ceramic tiles"
        )

    if "1200" not in display_answer:
        problems.append(
            "Q10 answer should mention 1200 kg"
        )

    dumped = json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
    ).lower()

    if "provisional" not in dumped:
        problems.append(
            "Q10 provisional duty wording missing"
        )

    return problems

VALIDATORS = {
    "q1": validate_q1,
    "q2": validate_q2,
    "q3": validate_q3,
    "q4": validate_q4,
    "q5": validate_q5,
    "q6": validate_q6,
    "q7": validate_q7,
    "q8": validate_q8,
    "q9": validate_q9,
    "q10": validate_q10,
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

    print("ALL TEN JSON REGRESSION CASES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
