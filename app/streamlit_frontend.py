from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.compact_frontend_payload import build_compact_frontend_payload
from app.frontend_payload import build_frontend_payload
from app.user_agent import run_user_agent_from_files, run_user_agent_from_text


SAMPLE_SHOPPING_REQUEST = ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
SAMPLE_INVOICE = ROOT_DIR / "data" / "documents" / "sample_invoice.txt"
SAMPLE_PACKING_LIST = ROOT_DIR / "data" / "documents" / "sample_packing_list.txt"


def humanize(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, (int, float)):
        return str(value)

    text = str(value).strip()

    acronyms = {
        "cbm": "CBM",
        "kg": "kg",
        "fcl": "FCL",
        "lcl": "LCL",
        "usa": "USA",
        "usd": "USD",
        "ai": "AI",
        "id": "ID",
        "hs": "HS",
        "msds": "MSDS",
        "un38.3": "UN38.3",
        "exw": "EXW",
        "fob": "FOB",
        "cif": "CIF",
        "dap": "DAP",
        "ddp": "DDP",
    }

    small_words = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}

    text = text.replace("_", " ").replace("-", " ")
    words = []

    for index, word in enumerate(text.split()):
        lowered = word.lower()

        if lowered in acronyms:
            words.append(acronyms[lowered])
        elif index > 0 and lowered in small_words:
            words.append(lowered)
        else:
            words.append(word[:1].upper() + word[1:])

    return " ".join(words)


def status_color(status: Any) -> str:
    lowered = str(status or "").lower()

    if "critical" in lowered or "blocked" in lowered or "failed" in lowered:
        return "red"

    if "review" in lowered or "missing" in lowered or "not_configured" in lowered:
        return "orange"

    if "ready" in lowered or "clear" in lowered or "available" in lowered:
        return "green"

    return "gray"


def badge(label: Any) -> str:
    color = status_color(label)
    return f":{color}-badge[{humanize(label)}]"


def get_sample_shopping_payload() -> dict[str, Any]:
    full_payload = process_json_file_request(SAMPLE_SHOPPING_REQUEST)
    return build_compact_frontend_payload(full_payload)


def get_text_payload(text_request: str) -> dict[str, Any]:
    raw_response = run_user_agent_from_text(text_request)
    full_payload = build_frontend_payload(raw_response)
    return build_compact_frontend_payload(full_payload)


def get_document_payload() -> dict[str, Any]:
    raw_response = run_user_agent_from_files([SAMPLE_INVOICE, SAMPLE_PACKING_LIST])
    full_payload = build_frontend_payload(raw_response)
    return build_compact_frontend_payload(full_payload)


def render_metric_cards(metrics: dict[str, Any], columns: int = 4) -> None:
    if not isinstance(metrics, dict) or not metrics:
        st.info("No metrics available.")
        return

    filtered_items = [(key, value) for key, value in metrics.items() if value not in [None, "", [], {}]]

    if not filtered_items:
        st.info("No metrics available.")
        return

    cols = st.columns(columns)

    for index, (key, value) in enumerate(filtered_items):
        with cols[index % columns]:
            if isinstance(value, list):
                display = ", ".join(humanize(item) for item in value)
            elif isinstance(value, dict):
                display = "; ".join(
                    f"{humanize(child_key)}: {humanize(child_value)}"
                    for child_key, child_value in value.items()
                    if child_value not in [None, "", [], {}]
                )
            else:
                display = humanize(value)

            st.metric(humanize(key), display)


def render_list(title: str, items: list[Any]) -> None:
    if not isinstance(items, list) or not items:
        return

    st.markdown(f"**{title}**")

    for item in items:
        st.markdown(f"- {humanize(item)}")


def render_executive_summary(payload: dict[str, Any]) -> None:
    executive = payload.get("executive_summary", {})
    final_answer = payload.get("final_answer", {})

    st.subheader("Executive Summary")

    headline = executive.get("headline") or final_answer.get("headline") or payload.get("short_answer")
    st.markdown(f"### {humanize(headline)}")

    cols = st.columns(4)

    with cols[0]:
        st.metric("Decision", humanize(payload.get("decision")))

    with cols[1]:
        st.metric("Booking Score", executive.get("booking_score"))

    with cols[2]:
        st.metric("First Pass", humanize(executive.get("ready_for_first_pass")))

    with cols[3]:
        st.metric("Ready for Booking", humanize(executive.get("ready_for_booking")))

    st.markdown(
        " ".join(
            [
                badge(payload.get("decision")),
                badge(executive.get("status")),
                badge(payload.get("partner_review_status")),
            ]
        )
    )


def render_logistics_visualizer(visualizer: dict[str, Any]) -> None:
    if not isinstance(visualizer, dict) or not visualizer:
        st.info("No logistics visualizer payload available.")
        return

    st.subheader("Logistics Visualizer")

    container = visualizer.get("container", {})
    cargo_mix = visualizer.get("cargo_mix", [])
    zone_layout = visualizer.get("zone_layout", [])
    loading_sequence = visualizer.get("loading_sequence", [])
    fit_check = visualizer.get("fit_check", {})

    st.markdown(badge(visualizer.get("status")))

    utilization = container.get("utilization_percent") or 0

    try:
        utilization_float = max(0.0, min(100.0, float(utilization)))
    except Exception:
        utilization_float = 0.0

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("#### Container")
        render_metric_cards(container, columns=2)

    with right:
        st.markdown("#### Utilization")
        st.progress(utilization_float / 100)
        st.caption(f"{utilization_float:.2f}% utilization")

        st.markdown("#### Fit Check")
        st.markdown(badge(fit_check.get("status")))
        render_list("Warnings", fit_check.get("warnings", []))
        render_list("Recommendations", fit_check.get("recommendations", []))

    if cargo_mix:
        st.markdown("#### Cargo Mix")
        st.dataframe(cargo_mix, use_container_width=True)

    if zone_layout:
        st.markdown("#### Zone Layout")
        zone_cols = st.columns(min(3, max(1, len(zone_layout))))

        for index, zone in enumerate(zone_layout):
            with zone_cols[index % len(zone_cols)]:
                st.markdown(f"**{humanize(zone.get('zone_name'))}**")
                st.caption(humanize(zone.get("description")))

                for item in zone.get("items", []):
                    st.markdown(
                        f"- **{humanize(item.get('item_name'))}** x {humanize(item.get('quantity'))} "
                        f"(Step {humanize(item.get('sequence_number'))})"
                    )

    if loading_sequence:
        st.markdown("#### Loading Sequence")

        for step in loading_sequence:
            with st.expander(
                f"Step {humanize(step.get('sequence_number'))}: {humanize(step.get('item_name'))} x {humanize(step.get('quantity'))}",
                expanded=False,
            ):
                st.markdown(f"**Zone:** {humanize(step.get('suggested_zone'))}")
                st.markdown(f"**Reason:** {humanize(step.get('reason'))}")
                tags = step.get("category_tags", [])
                if tags:
                    st.markdown(" ".join(badge(tag) for tag in tags))


def render_ui_sections(payload: dict[str, Any]) -> None:
    sections = payload.get("ui_sections", [])

    if not isinstance(sections, list) or not sections:
        return

    st.subheader("Review Sections")

    for section in sections:
        if not isinstance(section, dict):
            continue

        with st.expander(f"{section.get('title')} — {humanize(section.get('status'))}", expanded=False):
            st.markdown(f"**Status:** {badge(section.get('status'))}")
            st.markdown(humanize(section.get("summary")))

            metrics = section.get("metrics", {})
            if metrics:
                render_metric_cards(metrics, columns=3)

            render_list("Notes", section.get("bullets", []))
            render_list("Actions", section.get("actions", []))


def render_booking_and_actions(payload: dict[str, Any]) -> None:
    booking = payload.get("booking_readiness", {})
    action_plan = payload.get("action_plan", {})

    st.subheader("Booking Readiness & Action Plan")

    render_metric_cards(
        {
            "booking_status": booking.get("status"),
            "score": booking.get("score"),
            "ready_for_first_pass": booking.get("ready_for_first_pass"),
            "ready_for_booking": booking.get("ready_for_booking"),
            "next_gate": booking.get("next_gate"),
        },
        columns=5,
    )

    col1, col2 = st.columns(2)

    with col1:
        render_list("Missing Information", booking.get("missing_information", []))
        render_list("Review Items", booking.get("review_items", []))

    with col2:
        render_list("Before Booking", action_plan.get("before_booking", []))
        render_list("Partner Steps", action_plan.get("partner_steps", []))
        render_list("User Questions", action_plan.get("user_questions", []))


def render_payload(payload: dict[str, Any]) -> None:
    render_executive_summary(payload)

    st.divider()

    st.subheader("Logistics Metrics")
    render_metric_cards(payload.get("logistics_metrics", {}), columns=4)

    st.divider()

    render_logistics_visualizer(payload.get("logistics_visualizer", {}))

    st.divider()

    render_booking_and_actions(payload)

    st.divider()

    render_ui_sections(payload)

    st.divider()

    st.subheader("Backend Validation")
    render_metric_cards(payload.get("backend_validation", {}), columns=3)

    with st.expander("Raw Compact Payload", expanded=False):
        st.json(payload)


def main() -> None:
    st.set_page_config(
        page_title="Logistics Agent Frontend",
        page_icon="🚢",
        layout="wide",
    )

    st.title("Logistics Agent Frontend")
    st.caption("Interactive demo frontend using the backend compact frontend payload.")

    st.sidebar.header("Demo Input")

    mode = st.sidebar.radio(
        "Choose input flow",
        [
            "Sample shopping request",
            "Plain English request",
            "Sample documents",
        ],
    )

    if mode == "Sample shopping request":
        st.sidebar.info("Uses data/suppliers/sample_shopping_request.json")
        payload = get_sample_shopping_payload()

    elif mode == "Plain English request":
        default_text = (
            "I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
            "Prefer suppliers from India. Avoid China. Budget 13000 USD."
        )
        text_request = st.sidebar.text_area("Request", value=default_text, height=170)

        if st.sidebar.button("Run text request") or "text_payload" not in st.session_state:
            st.session_state.text_payload = get_text_payload(text_request)

        payload = st.session_state.text_payload

    else:
        st.sidebar.info("Uses sample invoice and packing list.")
        payload = get_document_payload()

    st.sidebar.divider()
    st.sidebar.markdown("### Payload Status")
    st.sidebar.markdown(f"Decision: **{humanize(payload.get('decision'))}**")
    st.sidebar.markdown(f"Intent: **{humanize(payload.get('detected_intent'))}**")
    st.sidebar.markdown(f"Partner: **{humanize(payload.get('partner_review_status'))}**")

    render_payload(payload)


if __name__ == "__main__":
    main()
