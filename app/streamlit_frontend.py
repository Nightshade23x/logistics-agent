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


def is_empty(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str) and not value.strip():
        return True

    if isinstance(value, (list, dict)) and not value:
        return True

    return False


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
        "eur": "EUR",
        "gbp": "GBP",
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


def display_value(value: Any, fallback: str = "Not available") -> str:
    if is_empty(value):
        return fallback

    if isinstance(value, list):
        if not value:
            return fallback
        return ", ".join(humanize(item) for item in value)

    if isinstance(value, dict):
        parts = []

        for key, child in value.items():
            if not is_empty(child):
                parts.append(f"{humanize(key)}: {humanize(child)}")

        return "; ".join(parts) if parts else fallback

    return humanize(value) or fallback


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
            "report",
            "text",
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


def get_raw_report_text(raw_response: Any) -> str:
    for text in walk_text_values(raw_response):
        if "SHOPPING AGENT REPORT" in text or "DOCUMENT" in text or "LOGISTICS" in text:
            return text

    return ""


def extract_requested_items(question: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"\b(?P<quantity>\d+)\s+(?P<item>[A-Za-z][A-Za-z0-9 /-]*?)(?=,| and |\.\s| from | under | below | within | with | budget |$)",
        re.IGNORECASE,
    )

    currency_words = {"usd", "eur", "gbp", "dollar", "dollars", "budget", "cost", "price", "k", "kwacha"}

    items: list[dict[str, str]] = []

    for match in pattern.finditer(question or ""):
        quantity = match.group("quantity").strip()
        item = match.group("item").strip(" .,").lower()

        if not item or item in currency_words:
            continue

        if any(word in item.split() for word in currency_words):
            continue

        if len(item) > 45:
            continue

        items.append({"quantity": quantity, "item": item})

    return items


def extract_budget(question: str) -> dict[str, Any]:
    patterns = [
        r"(?:under|below|within|budget|max(?:imum)?(?: budget)?(?: of)?|limit(?: of)?)\s*(?P<amount>\d+(?:\.\d+)?)\s*(?P<currency>usd|eur|gbp|\$)?",
        r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<currency>usd|eur|gbp|\$)\s*(?:budget|limit)?",
    ]

    for pattern in patterns:
        match = re.search(pattern, question or "", flags=re.IGNORECASE)

        if match:
            currency = match.groupdict().get("currency") or "USD"
            currency = "USD" if currency == "$" else currency.upper()

            return {
                "amount": float(match.group("amount")),
                "currency": currency,
            }

    return {}


def extract_country_list(question: str, keyword: str) -> list[str]:
    if keyword == "avoid":
        pattern = r"\bavoid\s+(?P<countries>[A-Za-z ,]+?)(?=\.|;|$)"
    else:
        pattern = r"\b(?:from|prefer(?: suppliers from)?)\s+(?P<countries>[A-Z][A-Za-z ,]+?)(?=\.|,| under | below | within | budget | avoid |$)"

    match = re.search(pattern, question or "", flags=re.IGNORECASE)

    if not match:
        return []

    raw = match.group("countries")
    countries = re.split(r"\s+and\s+|,", raw, flags=re.IGNORECASE)

    cleaned = []

    for country in countries:
        value = country.strip(" .")

        if value and len(value) <= 30:
            cleaned.append(value)

    return cleaned


def parse_raw_shopping_report(report_text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}

    if not report_text:
        return parsed

    status_match = re.search(r"(?:Shopping Agent status|Status):\s*([A-Za-z_]+)", report_text, flags=re.IGNORECASE)
    selected_match = re.search(r"Selected suppliers:\s*(\d+)", report_text, flags=re.IGNORECASE)
    cost_match = re.search(r"Estimated total procurement cost:\s*([0-9.]+)\s*USD", report_text, flags=re.IGNORECASE)
    budget_match = re.search(r"Budget limit:\s*([0-9.]+)\s*USD", report_text, flags=re.IGNORECASE)
    risk_match = re.search(r"Overall risk level:\s*([A-Za-z_]+)", report_text, flags=re.IGNORECASE)
    destination_match = re.search(r"Destination country:\s*([A-Za-z_]+)", report_text, flags=re.IGNORECASE)
    supplier_options_match = re.search(r"Shortlisted\s*(\d+)\s*supplier option", report_text, flags=re.IGNORECASE)
    excluded_match = re.search(r"Excluded supplier countries:\s*\[([^\]]*)\]", report_text, flags=re.IGNORECASE)

    if status_match:
        parsed["status"] = status_match.group(1)

    if selected_match:
        parsed["selected_suppliers"] = int(selected_match.group(1))

    if supplier_options_match:
        parsed["shortlisted_supplier_options"] = int(supplier_options_match.group(1))

    if cost_match:
        parsed["estimated_procurement_cost_usd"] = float(cost_match.group(1))

    if budget_match:
        parsed["budget_limit_usd"] = float(budget_match.group(1))

    if risk_match:
        parsed["overall_risk_level"] = risk_match.group(1)

    if destination_match:
        destination = destination_match.group(1)
        parsed["destination_country"] = None if destination.lower() == "none" else destination

    if excluded_match:
        countries = []
        raw = excluded_match.group(1)

        for quoted_single, quoted_double in re.findall(r"'([^']+)'|\"([^\"]+)\"", raw):
            countries.append(quoted_single or quoted_double)

        parsed["excluded_supplier_countries"] = countries

    return parsed


def get_sample_shopping_payload() -> dict[str, Any]:
    full_payload = process_json_file_request(SAMPLE_SHOPPING_REQUEST)
    compact_payload = build_compact_frontend_payload(full_payload)
    compact_payload["_source"] = "Sample shopping request"
    return compact_payload


def get_text_payload(text_request: str) -> dict[str, Any]:
    raw_response = run_user_agent_from_text(text_request)
    full_payload = build_frontend_payload(raw_response)
    compact_payload = build_compact_frontend_payload(full_payload)

    report_text = get_raw_report_text(raw_response)
    parsed_report = parse_raw_shopping_report(report_text)
    extracted_items = extract_requested_items(text_request)
    budget = extract_budget(text_request)

    compact_payload["_source"] = "Custom question"
    compact_payload["_question"] = text_request
    compact_payload["_extracted_items"] = extracted_items
    compact_payload["_budget"] = budget
    compact_payload["_preferred_supplier_countries"] = extract_country_list(text_request, keyword="from")
    compact_payload["_excluded_supplier_countries"] = extract_country_list(text_request, keyword="avoid")
    compact_payload["_raw_report_text"] = report_text
    compact_payload["_parsed_report"] = parsed_report
    compact_payload["_raw_user_agent_response"] = json_safe(raw_response)

    if is_empty(compact_payload.get("decision")) and parsed_report.get("status"):
        compact_payload["decision"] = parsed_report["status"]

    if is_empty(compact_payload.get("detected_intent")):
        compact_payload["detected_intent"] = "shopping"

    if not compact_payload.get("agents_called"):
        compact_payload["agents_called"] = ["shopping_agent"]

    if is_empty(compact_payload.get("partner_review_status")):
        compact_payload["partner_review_status"] = "not_run"

    if budget and "budget_limit_usd" not in parsed_report and budget.get("currency") == "USD":
        parsed_report["budget_limit_usd"] = budget.get("amount")

    if compact_payload.get("logistics_metrics") is None:
        compact_payload["logistics_metrics"] = {}

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


def extract_answer_text(payload: dict[str, Any]) -> str:
    candidates: list[str] = []

    for key in ["short_answer", "summary", "message", "answer", "final_answer"]:
        if key in payload:
            candidates.extend(walk_text_values(payload[key]))

    for candidate in candidates:
        text = candidate.strip()

        if len(text) < 8:
            continue

        low_quality = [
            "None CBM",
            "None Kg",
            "Recommended Container None",
            "Risk Level None",
            "SHOPPING AGENT REPORT",
            "PURCHASE ORDER DRAFTS",
        ]

        if any(marker in text for marker in low_quality):
            continue

        if len(text) > 900:
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


def build_frontend_answer(payload: dict[str, Any]) -> str:
    explicit_answer = extract_answer_text(payload)

    if explicit_answer:
        return explicit_answer

    intent = humanize(payload.get("detected_intent") or "request").lower()
    decision = humanize(payload.get("decision") or "needs_more_information").lower()
    parsed_report = payload.get("_parsed_report", {}) or {}
    extracted_items = payload.get("_extracted_items", []) or []
    budget = payload.get("_budget", {}) or {}
    preferred = payload.get("_preferred_supplier_countries", []) or []
    excluded = payload.get("_excluded_supplier_countries", []) or parsed_report.get("excluded_supplier_countries", [])

    item_text = ""

    if extracted_items:
        item_text = " It detected " + ", ".join(
            f"{item['quantity']} {item['item']}" for item in extracted_items
        ) + "."

    budget_text = ""

    if budget:
        budget_text = f" The detected budget is {budget.get('amount'):g} {budget.get('currency', 'USD')}."

    country_text_parts = []

    if preferred:
        country_text_parts.append("preferred supplier country: " + ", ".join(preferred))

    if excluded:
        country_text_parts.append("excluded supplier country: " + ", ".join(excluded))

    country_text = ""

    if country_text_parts:
        country_text = " It also detected " + "; ".join(country_text_parts) + "."

    selected_suppliers = parsed_report.get("selected_suppliers")
    shortlisted = parsed_report.get("shortlisted_supplier_options")

    if "shopping" in intent:
        if selected_suppliers == 0 or shortlisted == 0:
            return (
                f"The backend understood this as a shopping/procurement request and returned {decision}."
                f"{item_text}{budget_text}{country_text} "
                "No suppliers were shortlisted, so the logistics and booking sections cannot be completed yet. "
                "This usually means the custom products do not match the current local supplier catalog closely enough, "
                "or the request needs more structured product details."
            )

        return (
            f"The backend processed this as a shopping/procurement request and returned {decision}."
            f"{item_text}{budget_text}{country_text} Review the procurement summary and supplier output before running logistics."
        )

    return (
        f"The backend processed the request and returned {decision}. More structured details may be needed before the "
        "frontend can show a complete plan."
    )


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
            st.metric(humanize(key), display_value(value, fallback="Not available"))


def render_list(title: str, items: list[Any]) -> None:
    if not isinstance(items, list) or not items:
        return

    st.markdown(f"**{title}**")

    for item in items:
        st.markdown(f"- {humanize(item)}")


def render_executive_summary(payload: dict[str, Any]) -> None:
    executive = payload.get("executive_summary", {})
    parsed_report = payload.get("_parsed_report", {}) or {}

    st.subheader("Executive Summary")
    st.markdown(f"### {get_clean_headline(payload)}")

    metrics = {
        "decision": payload.get("decision") or parsed_report.get("status"),
        "intent": payload.get("detected_intent"),
        "partner_status": payload.get("partner_review_status"),
        "booking_score": executive.get("booking_score"),
    }

    render_metric_cards(metrics, columns=4)

    st.markdown(
        " ".join(
            badge(item)
            for item in [
                metrics.get("decision"),
                executive.get("status"),
                payload.get("partner_review_status"),
            ]
            if item
        )
    )


def render_agent_answer(payload: dict[str, Any]) -> None:
    st.subheader("Backend Answer")

    answer_text = build_frontend_answer(payload)
    decision = str(payload.get("decision") or "").lower()

    if "critical" in decision:
        st.error(answer_text)
    elif "need" in decision or "missing" in decision or "review" in decision:
        st.warning(answer_text)
    else:
        st.success(answer_text)

    agents_called = payload.get("agents_called", []) or []

    render_metric_cards(
        {
            "decision": payload.get("decision"),
            "detected_intent": payload.get("detected_intent"),
            "agents_called": agents_called,
            "partner_review_status": payload.get("partner_review_status"),
        },
        columns=4,
    )

    extracted_items = payload.get("_extracted_items", []) or []
    budget = payload.get("_budget", {}) or {}

    if extracted_items:
        st.markdown("#### Items detected from custom question")
        st.dataframe(extracted_items, use_container_width=True, hide_index=True)

    if budget:
        st.markdown("#### Budget detected")
        render_metric_cards(
            {
                "budget_amount": budget.get("amount"),
                "budget_currency": budget.get("currency"),
            },
            columns=2,
        )

    missing = collect_missing_information(payload)

    st.markdown("#### Next information needed")

    if missing:
        for item in missing[:12]:
            st.markdown(f"- {humanize(item)}")
    elif not payload.get("logistics_metrics"):
        for item in [
            "Destination country",
            "Origin country or selected supplier location",
            "Incoterm or shipping terms",
            "Selected supplier quote",
            "Unit dimensions for each item",
            "Unit weight for each item",
            "Cargo value, freight quote, insurance, duty, and tax inputs",
        ]:
            st.markdown(f"- {item}")


def render_procurement_summary(payload: dict[str, Any]) -> None:
    st.subheader("Procurement Summary")

    parsed_report = payload.get("_parsed_report", {}) or {}
    budget = payload.get("_budget", {}) or {}
    preferred = payload.get("_preferred_supplier_countries", []) or []
    excluded = payload.get("_excluded_supplier_countries", []) or parsed_report.get("excluded_supplier_countries", [])

    metrics = {
        "status": parsed_report.get("status") or payload.get("decision"),
        "selected_suppliers": parsed_report.get("selected_suppliers"),
        "shortlisted_supplier_options": parsed_report.get("shortlisted_supplier_options"),
        "estimated_procurement_cost_usd": parsed_report.get("estimated_procurement_cost_usd"),
        "budget_limit_usd": parsed_report.get("budget_limit_usd") or budget.get("amount"),
        "overall_risk_level": parsed_report.get("overall_risk_level"),
        "destination_country": parsed_report.get("destination_country"),
        "preferred_supplier_countries": preferred,
        "excluded_supplier_countries": excluded,
    }

    render_metric_cards(metrics, columns=4)

    raw_report = payload.get("_raw_report_text")

    if raw_report:
        with st.expander("Generated Shopping Agent Report", expanded=False):
            st.text(raw_report)


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

    if not isinstance(booking, dict):
        booking = {}

    if not isinstance(action_plan, dict):
        action_plan = {}

    metrics = {
        "booking_status": booking.get("status"),
        "score": booking.get("score"),
        "ready_for_first_pass": booking.get("ready_for_first_pass"),
        "ready_for_booking": booking.get("ready_for_booking"),
        "next_gate": booking.get("next_gate"),
    }

    render_metric_cards(metrics, columns=5)

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

    render_agent_answer(payload)

    st.divider()

    answer_tab, procurement_tab, logistics_tab, review_tab, raw_tab = st.tabs(
        [
            "Answer & Status",
            "Procurement",
            "Logistics Visualizer",
            "Review Sections",
            "Raw Payload",
        ]
    )

    with answer_tab:
        render_booking_and_actions(payload)

        st.divider()

        st.subheader("Backend Validation")
        render_metric_cards(payload.get("backend_validation", {}), columns=3)

    with procurement_tab:
        render_procurement_summary(payload)

    with logistics_tab:
        st.subheader("Logistics Metrics")
        render_metric_cards(payload.get("logistics_metrics", {}), columns=4)

        st.divider()

        render_logistics_visualizer(payload.get("logistics_visualizer", {}))

    with review_tab:
        render_ui_sections(payload)

    with raw_tab:
        st.subheader("Raw Compact Payload")
        st.caption("Useful for debugging frontend/backend contract issues.")

        raw_report = payload.get("_raw_report_text")

        if raw_report:
            with st.expander("Generated Text Report", expanded=False):
                st.text(raw_report)

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
            placeholder="Example: I need 20 laptops from India under 12000 USD. Avoid China. What suppliers and shipping plan should I use?",
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
    st.sidebar.markdown(f"Decision: **{display_value(payload.get('decision'), fallback='Not available')}**")
    st.sidebar.markdown(f"Intent: **{display_value(payload.get('detected_intent'), fallback='Not available')}**")
    st.sidebar.markdown(f"Partner: **{display_value(payload.get('partner_review_status'), fallback='Not run')}**")

    st.divider()

    render_payload(payload)


if __name__ == "__main__":
    main()
