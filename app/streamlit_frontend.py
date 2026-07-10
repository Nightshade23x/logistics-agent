from __future__ import annotations

import json
import re
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

DEFAULT_TEXT_REQUEST = (
    "I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
    "Prefer suppliers from India. Avoid China. Budget 13000 USD."
)


def humanize(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, (int, float)):
        return str(value)

    text = str(value).strip()

    if not text:
        return ""

    sentence_like = (
        len(text) > 70
        or "." in text
        or "?" in text
        or "!" in text
        or "; " in text
    )

    if sentence_like and "_" not in text:
        return text

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

    small_words = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }

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


def is_empty(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str) and not value.strip():
        return True

    if isinstance(value, (list, dict)) and not value:
        return True

    return False


def status_color(status: Any) -> str:
    lowered = str(status or "").lower()

    if "critical" in lowered or "blocked" in lowered or "failed" in lowered:
        return "red"

    if "review" in lowered or "missing" in lowered or "need" in lowered or "not_configured" in lowered:
        return "orange"

    if "ready" in lowered or "clear" in lowered or "available" in lowered:
        return "green"

    return "gray"


def badge(label: Any) -> str:
    if is_empty(label):
        return ""

    color = status_color(label)
    return f":{color}-badge[{humanize(label)}]"


def json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def extract_requested_items(question: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"(?P<quantity>\d+)\s+(?P<item>[A-Za-z][A-Za-z0-9 /-]*?)(?=,| and |\.\s| from | under | below | within | with |$)",
        re.IGNORECASE,
    )

    items = []

    for match in pattern.finditer(question or ""):
        quantity = match.group("quantity").strip()
        item = match.group("item").strip(" .,")

        if item:
            items.append({"quantity": quantity, "item": item})

    return items


def get_sample_shopping_payload() -> dict[str, Any]:
    full_payload = process_json_file_request(SAMPLE_SHOPPING_REQUEST)
    compact_payload = build_compact_frontend_payload(full_payload)
    compact_payload["_source"] = "Sample shopping request"
    return compact_payload


def get_text_payload(text_request: str) -> dict[str, Any]:
    raw_response = run_user_agent_from_text(text_request)
    full_payload = build_frontend_payload(raw_response)
    compact_payload = build_compact_frontend_payload(full_payload)

    compact_payload["_source"] = "Custom question"
    compact_payload["_question"] = text_request
    compact_payload["_extracted_items"] = extract_requested_items(text_request)
    compact_payload["_raw_user_agent_response"] = json_safe(raw_response)

    return compact_payload


def get_document_payload() -> dict[str, Any]:
    raw_response = run_user_agent_from_files([SAMPLE_INVOICE, SAMPLE_PACKING_LIST])
    full_payload = build_frontend_payload(raw_response)
    compact_payload = build_compact_frontend_payload(full_payload)
    compact_payload["_source"] = "Sample documents"
    return compact_payload


def get_clean_headline(payload: dict[str, Any]) -> str:
    decision = humanize(payload.get("decision") or payload.get("status") or "review_required")
    intent = humanize(payload.get("detected_intent") or "request")

    lowered_decision = decision.lower()

    if "need" in lowered_decision or "missing" in lowered_decision:
        return f"{intent} needs more information before a reliable plan can be produced."

    if "critical" in lowered_decision or "high risk" in lowered_decision:
        return f"{intent} requires critical review before booking."

    if "ready" in lowered_decision:
        return f"{intent} is ready for review."

    if "review" in lowered_decision:
        return f"{intent} is ready for human review."

    return f"{intent} processed by the backend."


def walk_text_values(value: Any) -> list[str]:
    values: list[str] = []

    if isinstance(value, str):
        stripped = value.strip()

        if stripped:
            values.append(stripped)

    elif isinstance(value, dict):
        priority_keys = [
            "answer",
            "final_answer",
            "short_answer",
            "summary",
            "message",
            "recommendation",
            "next_step",
            "explanation",
            "reason",
        ]

        for key in priority_keys:
            if key in value:
                values.extend(walk_text_values(value[key]))

        for key, child in value.items():
            if key not in priority_keys:
                values.extend(walk_text_values(child))

    elif isinstance(value, list):
        for child in value:
            values.extend(walk_text_values(child))

    return values


def extract_answer_text(payload: dict[str, Any]) -> str:
    candidates: list[str] = []

    for key in ["short_answer", "summary", "message", "answer", "final_answer"]:
        if key in payload:
            candidates.extend(walk_text_values(payload[key]))

    raw_response = payload.get("_raw_user_agent_response")

    if raw_response:
        candidates.extend(walk_text_values(raw_response))

    for candidate in candidates:
        text = candidate.strip()

        if len(text) < 8:
            continue

        low_quality = [
            "None CBM",
            "None Kg",
            "Recommended Container None",
            "Risk Level None",
        ]

        if any(marker in text for marker in low_quality):
            continue

        return text

    return ""


def collect_missing_information(payload: dict[str, Any]) -> list[Any]:
    missing: list[Any] = []

    booking = payload.get("booking_readiness", {})
    action_plan = payload.get("action_plan", {})

    if isinstance(booking, dict):
        missing.extend(booking.get("missing_information", []) or [])
        missing.extend(booking.get("missing_inputs", []) or [])
        missing.extend(booking.get("review_items", []) or [])

    if isinstance(action_plan, dict):
        missing.extend(action_plan.get("user_questions", []) or [])
        missing.extend(action_plan.get("missing_information", []) or [])
        missing.extend(action_plan.get("before_booking", []) or [])

    for section in payload.get("ui_sections", []) or []:
        if not isinstance(section, dict):
            continue

        status = str(section.get("status", "")).lower()

        if "missing" in status or "need" in status or "review" in status:
            missing.extend(section.get("actions", []) or [])
            missing.extend(section.get("bullets", []) or [])

    cleaned: list[Any] = []
    seen = set()

    for item in missing:
        key = str(item).strip().lower()

        if not key or key in seen:
            continue

        seen.add(key)
        cleaned.append(item)

    return cleaned


def build_fallback_answer(payload: dict[str, Any]) -> str:
    intent = humanize(payload.get("detected_intent") or "request").lower()
    decision = humanize(payload.get("decision") or "needs_more_information").lower()
    agents_called = payload.get("agents_called", []) or []
    question = payload.get("_question", "")
    extracted_items = payload.get("_extracted_items", []) or []

    item_text = ""

    if extracted_items:
        item_text = " I detected these requested items: " + ", ".join(
            f"{item['quantity']} {item['item']}" for item in extracted_items
        ) + "."

    if "shopping" in intent:
        return (
            f"The backend treated this as a shopping/procurement request and returned {decision}."
            f"{item_text} "
            "It did not produce a full logistics plan because the custom question does not yet contain enough "
            "structured shipment information for reliable container planning. Add item dimensions, unit weights, "
            "origin, destination, Incoterm, and supplier choice to get logistics metrics."
        )

    if agents_called:
        return (
            f"The backend processed the request through {', '.join(humanize(agent) for agent in agents_called)} "
            f"and returned {decision}. More structured details are needed before the frontend can show a complete plan."
        )

    if question:
        return (
            "The backend received the custom question, but it did not return a complete frontend-ready answer. "
            "Use the raw payload tab to inspect the backend response."
        )

    return "The backend processed the request, but no detailed answer was returned."


def render_metric_cards(metrics: dict[str, Any], columns: int = 4) -> None:
    if not isinstance(metrics, dict) or not metrics:
        st.info("No metrics available.")
        return

    filtered_items = [(key, value) for key, value in metrics.items() if not is_empty(value)]

    if not filtered_items:
        st.info("No metrics available.")
        return

    cols = st.columns(max(1, columns))

    for index, (key, value) in enumerate(filtered_items):
        with cols[index % max(1, columns)]:
            if isinstance(value, list):
                display = ", ".join(humanize(item) for item in value)
            elif isinstance(value, dict):
                display = "; ".join(
                    f"{humanize(child_key)}: {humanize(child_value)}"
                    for child_key, child_value in value.items()
                    if not is_empty(child_value)
                )
            else:
                display = humanize(value)

            st.metric(humanize(key), display or "?")


def render_list(title: str, items: list[Any]) -> None:
    if not isinstance(items, list) or not items:
        return

    st.markdown(f"**{title}**")

    for item in items:
        st.markdown(f"- {humanize(item)}")


def render_executive_summary(payload: dict[str, Any]) -> None:
    executive = payload.get("executive_summary", {})

    st.subheader("Executive Summary")
    st.markdown(f"### {get_clean_headline(payload)}")

    cols = st.columns(4)

    with cols[0]:
        st.metric("Decision", humanize(payload.get("decision")) or "?")

    with cols[1]:
        st.metric("Intent", humanize(payload.get("detected_intent")) or "?")

    with cols[2]:
        st.metric("Partner Status", humanize(payload.get("partner_review_status")) or "?")

    with cols[3]:
        st.metric("Booking Score", executive.get("booking_score") or "?")

    st.markdown(
        " ".join(
            badge(item)
            for item in [
                payload.get("decision"),
                executive.get("status"),
                payload.get("partner_review_status"),
            ]
            if item
        )
    )


def render_agent_answer(payload: dict[str, Any]) -> None:
    st.subheader("Backend Answer")

    answer_text = extract_answer_text(payload) or build_fallback_answer(payload)
    decision = str(payload.get("decision") or "").lower()

    agents_called = payload.get("agents_called", []) or []
    extracted_items = payload.get("_extracted_items", []) or []

    if "critical" in decision:
        st.error(answer_text)
    elif "need" in decision or "missing" in decision or "review" in decision:
        st.warning(answer_text)
    else:
        st.success(answer_text)

    meta = {
        "decision": payload.get("decision"),
        "detected_intent": payload.get("detected_intent"),
        "agents_called": agents_called,
        "partner_review_status": payload.get("partner_review_status"),
    }

    render_metric_cards(meta, columns=4)

    if extracted_items:
        st.markdown("#### Items detected from custom question")
        st.dataframe(extracted_items, use_container_width=True)

    missing = collect_missing_information(payload)

    if missing:
        st.markdown("#### Information needed")
        for item in missing[:12]:
            st.markdown(f"- {humanize(item)}")
    elif not payload.get("logistics_metrics"):
        st.markdown("#### Information likely needed")
        for item in [
            "Origin country and destination country",
            "Incoterm or shipping terms",
            "Supplier selection or supplier quote",
            "Unit dimensions for each item",
            "Unit weight for each item",
            "Cargo value, freight quote, insurance, duty, and tax inputs",
        ]:
            st.markdown(f"- {item}")


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
        st.info("No review sections available.")
        return

    st.subheader("Review Sections")

    for section in sections:
        if not isinstance(section, dict):
            continue

        title = section.get("title") or "Review Section"
        status = humanize(section.get("status"))

        with st.expander(f"{title} ? {status}", expanded=False):
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
            "booking_status": booking.get("status") if isinstance(booking, dict) else None,
            "score": booking.get("score") if isinstance(booking, dict) else None,
            "ready_for_first_pass": booking.get("ready_for_first_pass") if isinstance(booking, dict) else None,
            "ready_for_booking": booking.get("ready_for_booking") if isinstance(booking, dict) else None,
            "next_gate": booking.get("next_gate") if isinstance(booking, dict) else None,
        },
        columns=5,
    )

    col1, col2 = st.columns(2)

    with col1:
        if isinstance(booking, dict):
            render_list("Missing Information", booking.get("missing_information", []))
            render_list("Review Items", booking.get("review_items", []))

    with col2:
        if isinstance(action_plan, dict):
            render_list("Before Booking", action_plan.get("before_booking", []))
            render_list("Partner Steps", action_plan.get("partner_steps", []))
            render_list("User Questions", action_plan.get("user_questions", []))


def render_payload(payload: dict[str, Any]) -> None:
    render_executive_summary(payload)

    st.divider()

    render_agent_answer(payload)

    st.divider()

    answer_tab, logistics_tab, review_tab, raw_tab = st.tabs(
        [
            "Answer & Status",
            "Logistics Visualizer",
            "Review Sections",
            "Raw Payload",
        ]
    )

    with answer_tab:
        st.subheader("Logistics Metrics")
        render_metric_cards(payload.get("logistics_metrics", {}), columns=4)

        st.divider()

        render_booking_and_actions(payload)

        st.divider()

        st.subheader("Backend Validation")
        render_metric_cards(payload.get("backend_validation", {}), columns=3)

    with logistics_tab:
        render_logistics_visualizer(payload.get("logistics_visualizer", {}))

    with review_tab:
        render_ui_sections(payload)

    with raw_tab:
        st.subheader("Raw Compact Payload")
        st.caption("Useful for debugging frontend/backend contract issues.")
        st.json(payload)


def main() -> None:
    st.set_page_config(
        page_title="Logistics Agent Frontend",
        page_icon="??",
        layout="wide",
    )

    st.title("Logistics Agent Frontend")
    st.caption("Interactive frontend using the backend compact frontend payload.")

    if "active_payload" not in st.session_state:
        with st.spinner("Loading sample shopping request..."):
            st.session_state.active_payload = get_sample_shopping_payload()
            st.session_state.active_source = "Sample shopping request"
            st.session_state.active_question = ""

    st.markdown("### Ask a Custom Question")

    with st.form("custom_question_form", clear_on_submit=False):
        custom_question = st.text_input(
            "Search or ask a procurement/logistics question",
            placeholder="Example: I need 20 laptops from India under 12000 USD. What suppliers and shipping plan should I use?",
        )

        submitted = st.form_submit_button("Run Custom Question", type="primary")

    if submitted:
        if not custom_question.strip():
            st.warning("Type a question first.")
        else:
            with st.spinner("Running backend user agent..."):
                st.session_state.active_payload = get_text_payload(custom_question.strip())
                st.session_state.active_source = "Custom question"
                st.session_state.active_question = custom_question.strip()

    st.sidebar.header("Demo Controls")

    mode = st.sidebar.radio(
        "Load a demo flow",
        [
            "Sample shopping request",
            "Plain English request",
            "Sample documents",
        ],
    )

    if st.sidebar.button("Load Selected Demo"):
        with st.spinner(f"Loading {mode}..."):
            if mode == "Sample shopping request":
                st.session_state.active_payload = get_sample_shopping_payload()
                st.session_state.active_source = "Sample shopping request"
                st.session_state.active_question = ""

            elif mode == "Plain English request":
                st.session_state.active_payload = get_text_payload(DEFAULT_TEXT_REQUEST)
                st.session_state.active_source = "Plain English request"
                st.session_state.active_question = DEFAULT_TEXT_REQUEST

            else:
                st.session_state.active_payload = get_document_payload()
                st.session_state.active_source = "Sample documents"
                st.session_state.active_question = ""

    st.sidebar.divider()
    st.sidebar.markdown("### Active Run")
    st.sidebar.markdown(f"Source: **{st.session_state.active_source}**")

    if st.session_state.active_question:
        st.sidebar.markdown("Question:")
        st.sidebar.info(st.session_state.active_question)

    payload = st.session_state.active_payload

    st.sidebar.divider()
    st.sidebar.markdown("### Payload Status")
    st.sidebar.markdown(f"Decision: **{humanize(payload.get('decision')) or '?'}**")
    st.sidebar.markdown(f"Intent: **{humanize(payload.get('detected_intent')) or '?'}**")
    st.sidebar.markdown(f"Partner: **{humanize(payload.get('partner_review_status')) or '?'}**")

    st.divider()

    render_payload(payload)


if __name__ == "__main__":
    main()
