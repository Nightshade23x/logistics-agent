from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


PROMPTS = [
    {
        "id": "01_ceramic_tiles_full_trade_payload",
        "prompt": (
            "estimate freight and find supplier for 100 ceramic tiles from India to USA. "
            "Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. "
            "Duty rate is 5 percent. Import tax rate is 8 percent."
        ),
    },
    {
        "id": "02_tvs_and_electric_scooters",
        "prompt": (
            "I want to ship 50 TVs and 5 electric scooters from India to USA. "
            "The TVs are fragile, scooters have batteries, use CIF, freight quote 3500 USD, "
            "insurance 600 USD, duty 8 percent, import tax 6 percent."
        ),
    },
    {
        "id": "03_mixed_household_and_fragile_cargo",
        "prompt": (
            "Find suppliers and shipping plan for 10 CBM ceramic tiles, 100 pillows, "
            "5 mattresses, and 100 glass bottles from India to USA. Glass bottles are fragile. Use FOB."
        ),
    },
    {
        "id": "04_radioactive_medical_equipment",
        "prompt": (
            "Can I export radioactive medical equipment from India to USA? "
            "Tell me compliance, risk, logistics, and documents needed."
        ),
    },
    {
        "id": "05_direct_trader_trade_plan",
        "prompt": (
            "Assess trade plan for ceramic tiles from India to USA. "
            "Give HS code, duty, FTA, and export strategy."
        ),
    },
    {
        "id": "06_missing_furniture_details",
        "prompt": (
            "I only know I need to import furniture to USA, maybe dining sets and mattresses, "
            "but I do not know dimensions or weight yet. What information do you need before booking?"
        ),
    },
]


def json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(k): json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [json_safe(v) for v in value]
        if isinstance(value, tuple):
            return [json_safe(v) for v in value]
        return str(value)


def load_runner():
    import app.user_agent as user_agent

    candidates = [
        "run_user_agent_from_text",
        "run_user_agent",
        "run_user_request",
        "handle_user_request",
        "process_user_request",
    ]

    for name in candidates:
        fn = getattr(user_agent, name, None)
        if callable(fn):
            return name, fn

    raise RuntimeError(
        "Could not find a runnable User Agent function. "
        "Checked: " + ", ".join(candidates)
    )


def call_runner(fn, prompt: str) -> Any:
    attempts = [
        lambda: fn(prompt),
        lambda: fn({"text": prompt}),
        lambda: fn({"question": prompt}),
        lambda: fn(text=prompt),
        lambda: fn(question=prompt),
    ]

    errors = []

    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            errors.append(str(exc))

    raise RuntimeError("Could not call User Agent runner. TypeErrors: " + " | ".join(errors))


def compact_summary(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"non_dict_result": str(result)}

    partner_review = result.get("partner_review") or {}
    partner_payload = result.get("partner_review_payload") or {}
    specialist_responses = result.get("specialist_responses") or {}

    return {
        "agent_name": result.get("agent_name"),
        "status": result.get("status"),
        "decision": result.get("decision"),
        "detected_intent": result.get("detected_intent"),
        "route_reason": result.get("route_reason"),
        "agents_called": result.get("agents_called"),
        "review_services_called": result.get("review_services_called"),
        "partner_review_status": result.get("partner_review_status"),
        "partner_review_mode": result.get("partner_review_mode"),
        "live_orchestrator_configured": result.get("live_orchestrator_configured"),
        "partner_review_attempted": result.get("partner_review_attempted"),
        "partner_agent_errors": (
            partner_review.get("agent_errors")
            or result.get("agent_errors")
            or {}
        ),
        "missing_information": result.get("missing_information"),
        "final_answer": result.get("final_answer"),
        "logistics_metrics": result.get("logistics_metrics"),
        "partner_review_payload": {
            "origin": partner_payload.get("origin"),
            "destination": partner_payload.get("destination"),
            "incoterm": partner_payload.get("incoterm"),
            "freight_quote_usd": partner_payload.get("freight_quote_usd"),
            "insurance_premium_usd": partner_payload.get("insurance_premium_usd"),
            "duty_rate_percent": partner_payload.get("duty_rate_percent"),
            "import_tax_rate_percent": partner_payload.get("import_tax_rate_percent"),
            "total_cbm": partner_payload.get("total_cbm"),
            "total_weight_kg": partner_payload.get("total_weight_kg"),
            "declared_value_usd": partner_payload.get("declared_value_usd"),
        },
        "specialist_statuses": {
            key: value.get("status") if isinstance(value, dict) else None
            for key, value in specialist_responses.items()
        },
    }


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / f"full_system_prompt_test_raw_{timestamp}.json"
    md_path = output_dir / f"full_system_prompt_test_report_{timestamp}.md"

    runner_name, runner = load_runner()

    records = []

    for index, case in enumerate(PROMPTS, start=1):
        print(f"\n[{index}/{len(PROMPTS)}] Running {case['id']}...")
        prompt = case["prompt"]

        try:
            result = call_runner(runner, prompt)
            safe_result = json_safe(result)
            summary = compact_summary(safe_result)
            error = None
        except Exception as exc:
            safe_result = None
            summary = {}
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }

        records.append(
            {
                "id": case["id"],
                "prompt": prompt,
                "runner": runner_name,
                "error": error,
                "summary": json_safe(summary),
                "raw_result": safe_result,
            }
        )

    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Full System Prompt Test Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Runner: `{runner_name}`")
    lines.append("")
    lines.append("## Test Cases")
    lines.append("")

    for record in records:
        lines.append(f"## {record['id']}")
        lines.append("")
        lines.append("### Prompt")
        lines.append("")
        lines.append(record["prompt"])
        lines.append("")

        if record["error"]:
            lines.append("### Error")
            lines.append("")
            lines.append("```text")
            lines.append(record["error"]["traceback"])
            lines.append("```")
            lines.append("")
            continue

        summary = record["summary"]

        lines.append("### Quick Summary")
        lines.append("")
        lines.append(f"- Status: `{summary.get('status')}`")
        lines.append(f"- Decision: `{summary.get('decision')}`")
        lines.append(f"- Detected intent: `{summary.get('detected_intent')}`")
        lines.append(f"- Agents called: `{summary.get('agents_called')}`")
        lines.append(f"- Review services called: `{summary.get('review_services_called')}`")
        lines.append(f"- Partner review status: `{summary.get('partner_review_status')}`")
        lines.append(f"- Partner review mode: `{summary.get('partner_review_mode')}`")
        lines.append(f"- Live orchestrator configured: `{summary.get('live_orchestrator_configured')}`")
        lines.append("")

        lines.append("### Logistics Metrics")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(summary.get("logistics_metrics"), indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        lines.append("### Partner Payload")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(summary.get("partner_review_payload"), indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        lines.append("### Missing Information")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(summary.get("missing_information"), indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        lines.append("### Final Answer")
        lines.append("")
        final_answer = summary.get("final_answer")
        if isinstance(final_answer, str):
            lines.append(final_answer)
        else:
            lines.append("```json")
            lines.append(json.dumps(final_answer, indent=2, ensure_ascii=False))
            lines.append("```")
        lines.append("")

        lines.append("### Specialist Statuses")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(summary.get("specialist_statuses"), indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("\nDONE")
    print(f"Markdown report: {md_path}")
    print(f"Raw JSON file:   {json_path}")


if __name__ == "__main__":
    main()
