from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backend_service import process_text_request


PROMPTS = {
    "q1": (
        "What is the HS code, import duty rate and FTA status for "
        "ceramic tiles exported from India to the USA?"
    ),
    "q2": (
        "Ship 1.2 CBM of lithium batteries weighing 1000 kg from "
        "India to Germany. The cargo is hazardous and non-stackable."
    ),
    "q3": (
        "Ship 10 CBM of ceramic tiles weighing 1200 kg from India "
        "to the USA under CIF."
    ),
    "q4": (
        "Find suppliers and plan shipping for 50 TVs, 5 scooters, "
        "100 pillows and 10 CBM of ceramic tiles from India to the "
        "USA under FOB."
    ),
    "q5": (
        "Calculate the landed cost for ceramic tiles shipped from "
        "India to the USA under CIF. Procurement value is USD 12000, "
        "freight quote is USD 3500, insurance premium is USD 600, "
        "duty rate is 8%, import tax rate is 6%, customs brokerage "
        "is USD 400 and local delivery is USD 800."
    ),
    "q6": (
        "Review the commercial invoice, packing list and "
        "dangerous-goods document requirements for shipping one "
        "pallet of lithium batteries from India to Germany under "
        "CIF. The cargo is hazardous."
    ),
}


def cargo_item(payload, name):
    visualizer = payload.get("logistics_visualizer") or {}

    for item in visualizer.get("cargo_mix") or []:
        if name in str(item.get("item_name", "")).lower():
            return item

    return None


def check(condition, message, failures):
    if not condition:
        failures.append(message)


def main():
    output_dir = (
        ROOT
        / "demo_outputs"
        / "json_regression_v11"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    all_failures = []

    for name, prompt in PROMPTS.items():
        payload = process_text_request(
            prompt,
            include_raw_response=False,
        )

        path = output_dir / f"{name}.json"
        path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        failures = []
        agents = payload.get("agents_called") or []
        metrics = payload.get("logistics_metrics") or {}
        visualizer = payload.get(
            "logistics_visualizer"
        ) or {}
        fit = visualizer.get("fit_check") or {}
        landed = payload.get("landed_cost_advice") or {}
        validation = payload.get(
            "backend_validation"
        ) or {}

        dumped = json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )

        if name == "q1":
            check(
                agents == ["trader_agent"],
                f"Q1 agents incorrect: {agents}",
                failures,
            )
            check(
                visualizer.get("status")
                == "unavailable",
                "Q1 visualizer must be unavailable.",
                failures,
            )
            check(
                "ceramic tiles exported"
                not in dumped.lower(),
                "Q1 product name is still polluted.",
                failures,
            )

        elif name == "q2":
            item = cargo_item(
                payload,
                "lithium batteries",
            )

            check(
                metrics.get("total_cbm") == 1.2,
                f"Q2 CBM incorrect: {metrics}",
                failures,
            )
            check(
                metrics.get("total_weight_kg")
                == 1000.0,
                f"Q2 weight incorrect: {metrics}",
                failures,
            )
            check(
                metrics.get("risk_level") == "high",
                f"Q2 risk incorrect: {metrics}",
                failures,
            )
            check(
                isinstance(item, dict)
                and item.get("stackable") is False,
                f"Q2 stackability incorrect: {item}",
                failures,
            )
            check(
                "Germany The cargo"
                not in dumped,
                "Q2 destination remains polluted.",
                failures,
            )

        elif name == "q3":
            item = cargo_item(
                payload,
                "ceramic tiles",
            )
            dimensions = (
                item.get("dimensions_m")
                if isinstance(item, dict)
                else {}
            ) or {}

            check(
                "logistics_agent" in agents
                and "trader_agent" in agents,
                f"Q3 agent chain incorrect: {agents}",
                failures,
            )
            check(
                metrics.get("total_cbm") == 10.0,
                f"Q3 CBM incorrect: {metrics}",
                failures,
            )
            check(
                metrics.get("total_weight_kg")
                == 1200.0,
                f"Q3 weight incorrect: {metrics}",
                failures,
            )
            check(
                dimensions.get("length") != 10.0,
                f"Q3 still uses fake 10m item: {item}",
                failures,
            )
            check(
                fit.get("status")
                == "fits_selected_container",
                f"Q3 fit status incorrect: {fit}",
                failures,
            )

        elif name == "q4":
            item = cargo_item(
                payload,
                "ceramic tiles",
            )
            dimensions = (
                item.get("dimensions_m")
                if isinstance(item, dict)
                else {}
            ) or {}

            check(
                all(
                    required in agents
                    for required in [
                        "shopping_agent",
                        "logistics_agent",
                        "trader_agent",
                    ]
                ),
                f"Q4 agent chain incorrect: {agents}",
                failures,
            )
            check(
                dimensions.get("length") != 10.0,
                f"Q4 still uses fake 10m tile: {item}",
                failures,
            )
            check(
                isinstance(item, dict)
                and item.get(
                    "aggregate_volume_only"
                )
                is True,
                f"Q4 aggregate marker missing: {item}",
                failures,
            )
            check(
                isinstance(item, dict)
                and item.get("total_weight_kg", 0)
                > 1000,
                f"Q4 tile weight remains unrealistic: {item}",
                failures,
            )
            check(
                "was could not"
                not in dumped.lower(),
                "Q4 grammar issue remains.",
                failures,
            )

        elif name == "q5":
            check(
                "trader_agent" in agents
                and "finance_agent" in agents,
                f"Q5 agents incorrect: {agents}",
                failures,
            )
            check(
                landed.get(
                    "estimated_landed_cost_usd"
                )
                == 19631.28,
                f"Q5 landed cost incorrect: {landed}",
                failures,
            )
            check(
                landed.get("missing_cost_inputs")
                == [],
                f"Q5 still reports missing costs: {landed}",
                failures,
            )
            check(
                visualizer.get("status")
                == "unavailable",
                "Q5 visualizer must be unavailable.",
                failures,
            )

        elif name == "q6":
            check(
                agents
                == [
                    "document_ai_agent",
                    "compliance_agent",
                ],
                f"Q6 agents incorrect: {agents}",
                failures,
            )
            check(
                validation.get(
                    "response_contract_valid"
                )
                is True,
                f"Q6 contract invalid: {validation}",
                failures,
            )
            check(
                (
                    payload.get(
                        "document_quality_review"
                    )
                    or {}
                ).get("applicable")
                is True,
                "Q6 Document AI review is not applicable.",
                failures,
            )
            check(
                (
                    payload.get(
                        "document_requirements_advice"
                    )
                    or {}
                ).get("item_count")
                == 1,
                "Q6 document item count must be one.",
                failures,
            )
            check(
                visualizer.get("status")
                == "unavailable",
                "Q6 visualizer must be unavailable.",
                failures,
            )

        print()
        print("=" * 88)
        print(name.upper())
        print("=" * 88)
        print("agents:", agents)
        print("metrics:", metrics)
        print(
            "visualizer:",
            visualizer.get("status"),
        )
        print("fit:", fit.get("status"))
        print(
            "landed_cost:",
            landed.get(
                "estimated_landed_cost_usd"
            ),
        )
        print(
            "contract_valid:",
            validation.get(
                "response_contract_valid"
            ),
        )
        print("saved:", path)

        if failures:
            print("FAIL")
            for failure in failures:
                print("-", failure)
                all_failures.append(failure)
        else:
            print("PASS")

    print()
    print("=" * 88)
    print("FINAL RESULT")
    print("=" * 88)

    if all_failures:
        print("FAILED CHECKS:")
        for failure in all_failures:
            print("-", failure)

        raise SystemExit(1)

    print("ALL SIX JSON REGRESSION CASES PASSED")


if __name__ == "__main__":
    main()
