from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.user_agent import (
    run_user_agent_from_files,
    run_user_agent_from_json_file,
    run_user_agent_from_text,
)


def _short(text: str | None, limit: int = 180) -> str:
    if not text:
        return ""

    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned

    return cleaned[:limit] + "..."


def _print_specialist_summaries(response: dict) -> None:
    specialist_responses = response.get("specialist_responses", {})

    if not specialist_responses:
        specialist = response.get("specialist_response")
        if specialist:
            specialist_responses = {specialist.get("agent_name", "specialist_agent"): specialist}

    if not specialist_responses:
        return

    print("Agent summaries:")
    for name, specialist_response in specialist_responses.items():
        if not isinstance(specialist_response, dict):
            continue

        print(
            f"- {name}: {specialist_response.get('status')} | "
            f"{_short(specialist_response.get('summary'))}"
        )


def _print_logistics_metrics(response: dict) -> None:
    logistics_response = response.get("specialist_responses", {}).get("logistics_agent", {})

    if not logistics_response:
        return

    handoff = logistics_response.get("handoff_payload", {})

    print("Logistics metrics:")
    print(f"- Total CBM: {handoff.get('total_cbm')}")
    print(f"- Total weight kg: {handoff.get('total_weight_kg')}")
    print(f"- Recommended container: {handoff.get('recommended_container')}")
    print(f"- Load type: {handoff.get('recommended_load_type')}")
    print(f"- Risk level: {handoff.get('risk_level')}")


def _print_partner_review(response: dict) -> None:
    partner_review = response.get("partner_review", {})

    if not partner_review:
        return

    print("Partner review:")
    print(f"- Status: {partner_review.get('status')}")
    print(f"- Summary: {_short(partner_review.get('summary'))}")


def _print_final_verdict(response: dict) -> None:
    final_verdict = response.get("final_verdict", {})

    if not final_verdict:
        return

    print("Final verdict:")
    print(f"- Decision: {final_verdict.get('verdict')}")

    for blocker in final_verdict.get("blockers", []):
        print(f"- Blocker: {blocker}")

    for warning in final_verdict.get("warnings", []):
        print(f"- Warning: {warning}")


def _print_missing_information(response: dict) -> None:
    missing_information = response.get("missing_information", [])

    print(f"Missing information count: {len(missing_information)}")

    for item in missing_information[:3]:
        print(f"- {item}")

    if len(missing_information) > 3:
        print(f"- ...and {len(missing_information) - 3} more")


def print_demo_result(title: str, response: dict) -> None:
    print("")
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"Status: {response.get('status')}")
    print(f"Detected intent: {response.get('detected_intent')}")
    print(f"Agents called: {response.get('agents_called')}")
    print(f"Summary: {_short(response.get('summary'))}")
    print("")

    _print_specialist_summaries(response)
    print("")
    _print_logistics_metrics(response)
    print("")
    _print_partner_review(response)
    print("")
    _print_final_verdict(response)
    print("")
    _print_missing_information(response)


def main() -> None:
    shopping_json = run_user_agent_from_json_file(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )
    print_demo_result(
        "DEMO 1: Shopping JSON -> Shopping Agent -> Logistics Agent -> Partner Review",
        shopping_json,
    )

    document_flow = run_user_agent_from_files(
        [
            ROOT_DIR / "data" / "documents" / "sample_invoice.txt",
            ROOT_DIR / "data" / "documents" / "sample_packing_list.txt",
        ]
    )
    print_demo_result(
        "DEMO 2: Documents -> Document AI Agent -> Logistics Agent -> Partner Review",
        document_flow,
    )

    text_flow = run_user_agent_from_text(
        "I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
        "Prefer suppliers from India. Avoid China. Budget 13000 USD."
    )
    print_demo_result(
        "DEMO 3: Plain English request -> Shopping Agent -> Logistics Agent",
        text_flow,
    )


if __name__ == "__main__":
    main()
