from __future__ import annotations

import html
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
from app.smart_answer import generate_smart_answer


SAMPLE_SHOPPING_REQUEST = ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
SAMPLE_INVOICE = ROOT_DIR / "data" / "documents" / "sample_invoice.txt"
SAMPLE_PACKING_LIST = ROOT_DIR / "data" / "documents" / "sample_packing_list.txt"

DEFAULT_TEXT_REQUEST = (
    "I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
    "Prefer suppliers from India. Avoid China. Budget 13000 USD."
)


def esc_html(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def inject_app_styles() -> None:
    st.markdown(
        """
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}

            .block-container {
                padding-top: 1.6rem;
                padding-bottom: 3rem;
                max-width: 1320px;
            }

            .app-hero {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 24px;
                padding: 28px 30px;
                margin-bottom: 22px;
                background:
                    radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 32%),
                    linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(17, 24, 39, 0.92));
                box-shadow: 0 16px 44px rgba(0, 0, 0, 0.24);
            }

            .app-eyebrow {
                color: #38bdf8;
                font-size: 0.82rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.13em;
                margin-bottom: 8px;
            }

            .app-title {
                color: #f8fafc;
                font-size: 2.45rem;
                font-weight: 900;
                line-height: 1.05;
                margin: 0 0 10px 0;
            }

            .app-subtitle {
                color: #cbd5e1;
                font-size: 1.02rem;
                line-height: 1.65;
                max-width: 940px;
                margin: 0;
            }

            .status-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 18px;
            }

            .status-chip {
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 999px;
                padding: 7px 12px;
                font-size: 0.82rem;
                font-weight: 800;
                color: #e5e7eb;
                background: rgba(15, 23, 42, 0.72);
            }

            .status-chip.good {
                color: #86efac;
                border-color: rgba(34, 197, 94, 0.34);
                background: rgba(22, 101, 52, 0.22);
            }

            .status-chip.warn {
                color: #fde68a;
                border-color: rgba(245, 158, 11, 0.38);
                background: rgba(146, 64, 14, 0.22);
            }

            .status-chip.bad {
                color: #fca5a5;
                border-color: rgba(239, 68, 68, 0.38);
                background: rgba(127, 29, 29, 0.24);
            }

            .kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 14px;
                margin: 14px 0 20px 0;
            }

            .kpi-card {
                border: 1px solid rgba(148, 163, 184, 0.20);
                border-radius: 18px;
                padding: 17px 18px;
                min-height: 104px;
                background: rgba(15, 23, 42, 0.72);
                box-shadow: 0 8px 28px rgba(0, 0, 0, 0.18);
            }

            .kpi-label {
                color: #94a3b8;
                font-size: 0.76rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 10px;
            }

            .kpi-value {
                color: #f8fafc;
                font-size: 1.22rem;
                font-weight: 900;
                line-height: 1.25;
                overflow-wrap: anywhere;
            }

            .panel-card {
                border: 1px solid rgba(148, 163, 184, 0.20);
                border-radius: 20px;
                padding: 22px 24px;
                margin: 14px 0 22px 0;
                background: rgba(15, 23, 42, 0.70);
                box-shadow: 0 10px 32px rgba(0, 0, 0, 0.18);
            }

            .answer-card {
                border-radius: 20px;
                padding: 22px 24px;
                margin: 14px 0 16px 0;
                font-size: 1.02rem;
                line-height: 1.68;
                border: 1px solid rgba(148, 163, 184, 0.22);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
            }

            .answer-card.warn {
                color: #fef3c7;
                background: linear-gradient(135deg, rgba(113, 63, 18, 0.58), rgba(63, 63, 16, 0.48));
                border-color: rgba(245, 158, 11, 0.32);
            }

            .answer-card.good {
                color: #dcfce7;
                background: linear-gradient(135deg, rgba(20, 83, 45, 0.58), rgba(6, 78, 59, 0.48));
                border-color: rgba(34, 197, 94, 0.32);
            }

            .answer-card.bad {
                color: #fee2e2;
                background: linear-gradient(135deg, rgba(127, 29, 29, 0.60), rgba(88, 28, 28, 0.48));
                border-color: rgba(239, 68, 68, 0.36);
            }

            .empty-card {
                border: 1px dashed rgba(148, 163, 184, 0.34);
                border-radius: 18px;
                padding: 20px 22px;
                margin: 12px 0 18px 0;
                background: rgba(15, 23, 42, 0.52);
            }

            .empty-title {
                color: #bfdbfe;
                font-size: 1rem;
                font-weight: 900;
                margin-bottom: 9px;
            }

            .empty-message {
                color: #cbd5e1;
                line-height: 1.65;
                margin-bottom: 0;
            }

            .stage-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 12px;
                margin: 14px 0 24px 0;
            }

            .stage-card {
                border: 1px solid rgba(148, 163, 184, 0.20);
                border-radius: 17px;
                padding: 16px 16px;
                background: rgba(15, 23, 42, 0.70);
            }

            .stage-card.done {
                border-color: rgba(34, 197, 94, 0.42);
                background: rgba(20, 83, 45, 0.24);
            }

            .stage-card.active {
                border-color: rgba(245, 158, 11, 0.46);
                background: rgba(113, 63, 18, 0.24);
            }

            .stage-card.pending {
                opacity: 0.72;
            }

            .stage-label {
                color: #f8fafc;
                font-size: 0.96rem;
                font-weight: 900;
                margin-bottom: 6px;
            }

            .stage-detail {
                color: #94a3b8;
                font-size: 0.82rem;
                line-height: 1.45;
            }

            .action-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
                margin: 14px 0 20px 0;
            }

            .action-card {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 18px;
                padding: 18px 20px;
                background: rgba(15, 23, 42, 0.70);
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
            }

            .action-card-title {
                color: #f8fafc;
                font-size: 1rem;
                font-weight: 900;
                margin-bottom: 10px;
            }

            .action-card ul {
                margin: 0;
                padding-left: 18px;
            }

            .action-card li {
                color: #cbd5e1;
                margin-bottom: 8px;
                line-height: 1.45;
            }

            .action-card li:last-child {
                margin-bottom: 0;
            }

            .section-title {
                margin-top: 8px;
                margin-bottom: 8px;
                color: #f8fafc;
                font-size: 1.35rem;
                font-weight: 900;
            }

            .section-caption {
                color: #94a3b8;
                font-size: 0.92rem;
                margin-bottom: 14px;
            }

            div[data-testid="stTabs"] button {
                font-weight: 800;
                font-size: 0.96rem;
            }

            div[data-testid="stDataFrame"] {
                border-radius: 16px;
                overflow: hidden;
            }

            @media (max-width: 980px) {
                .kpi-grid,
                .stage-grid,
                .action-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .app-title {
                    font-size: 2rem;
                }
            }

            @media (max-width: 620px) {
                .kpi-grid,
                .stage-grid,
                .action-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def chip_class(value: Any) -> str:
    lowered = str(value or "").lower()

    if "critical" in lowered or "blocked" in lowered or "failed" in lowered or "error" in lowered:
        return "bad"

    if "ready" in lowered or "clear" in lowered or "available" in lowered or "generated" in lowered:
        return "good"

    if "review" in lowered or "missing" in lowered or "need" in lowered or "not_configured" in lowered or "not_run" in lowered:
        return "warn"

    return ""


def render_chip(label: str, value: Any) -> str:
    if is_empty(value):
        value = "Not available"

    return (
        f'<span class="status-chip {chip_class(value)}">'
        f'{esc_html(label)}: {esc_html(display_value(value, fallback="Not available"))}'
        f'</span>'
    )


def render_app_header(payload: dict[str, Any]) -> None:
    chips = "".join(
        [
            render_chip("Decision", payload.get("decision")),
            render_chip("Intent", payload.get("detected_intent")),
            render_chip("Partner", payload.get("partner_review_status")),
        ]
    )

    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-eyebrow">Logistics Agent Demo</div>
            <h1 class="app-title">Procurement & Shipment Control Tower</h1>
            <p class="app-subtitle">
                Ask a buying or logistics question, review the agent output, and inspect procurement,
                logistics, booking readiness, partner-review status, and raw backend payloads in one place.
            </p>
            <div class="status-chip-row">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_grid(metrics: dict[str, Any], columns: int = 4) -> None:
    if not isinstance(metrics, dict) or not metrics:
        render_empty_state("No metrics available", "This section did not return structured metrics.")
        return

    cards = []

    for key, value in metrics.items():
        if is_empty(value):
            continue

        label = esc_html(humanize(key))
        displayed = esc_html(display_value(value, fallback="Not available"))
        cards.append(
            f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{displayed}</div></div>'
        )

    if not cards:
        render_empty_state("No metrics available", "This section did not return structured metrics.")
        return

    st.markdown(
        f'<div class="kpi-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def render_stage_tracker(payload: dict[str, Any]) -> None:
    parsed_report = payload.get("_parsed_report", {}) or {}
    logistics_metrics = payload.get("logistics_metrics", {}) or {}
    partner_status = str(payload.get("partner_review_status") or "").lower()
    booking = payload.get("booking_readiness", {}) if isinstance(payload.get("booking_readiness"), dict) else {}

    selected_suppliers = parsed_report.get("selected_suppliers")
    shortlisted = parsed_report.get("shortlisted_supplier_options")

    procurement_done = bool(
        payload.get("detected_intent") == "shopping"
        or payload.get("agents_called")
        or parsed_report
    )

    procurement_usable = bool(
        (selected_suppliers and selected_suppliers > 0)
        or (shortlisted and shortlisted > 0)
        or payload.get("logistics_metrics")
    )

    logistics_done = has_displayable_metrics(logistics_metrics)
    partner_done = partner_status not in ["", "not_run", "partner_review_not_configured", "not available"]
    booking_done = bool(booking.get("ready_for_booking"))

    stages = [
        {
            "label": "Procurement",
            "detail": "Supplier and item selection",
            "state": "done" if procurement_usable else ("active" if procurement_done else "pending"),
        },
        {
            "label": "Logistics",
            "detail": "CBM, weight, container, routing",
            "state": "done" if logistics_done else ("pending" if not procurement_usable else "active"),
        },
        {
            "label": "Partner Review",
            "detail": "Risk, compliance, trader, finance",
            "state": "done" if partner_done else ("pending" if not logistics_done else "active"),
        },
        {
            "label": "Booking",
            "detail": "Final readiness and actions",
            "state": "done" if booking_done else ("pending" if not partner_done else "active"),
        },
    ]

    cards = []

    for stage in stages:
        state = stage["state"]
        icon = "?" if state == "done" else ("?" if state == "active" else "?")
        label = esc_html(stage["label"])
        detail = esc_html(stage["detail"])
        cards.append(
            f'<div class="stage-card {state}"><div class="stage-label">{icon} {label}</div><div class="stage-detail">{detail}</div></div>'
        )

    st.markdown('<div class="section-title">Workflow Status</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="stage-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
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

    fallback_answer = build_frontend_answer(compact_payload)

    compact_payload["_smart_answer"] = generate_smart_answer(
        question=text_request,
        payload=compact_payload,
        fallback_answer=fallback_answer,
    )

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


def has_displayable_metrics(metrics: Any) -> bool:
    if not isinstance(metrics, dict):
        return False

    return any(not is_empty(value) for value in metrics.values())


def render_empty_state(title: str, message: str, bullets: list[str] | None = None) -> None:
    bullet_html = ""

    if bullets:
        bullet_html = "<ul>" + "".join(f"<li>{esc_html(bullet)}</li>" for bullet in bullets) + "</ul>"

    st.markdown(
        f"""
        <div class="empty-card">
            <div class="empty-title">{esc_html(title)}</div>
            <p class="empty-message">{esc_html(message)}</p>
            {bullet_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def is_custom_question_payload(payload: dict[str, Any]) -> bool:
    return payload.get("_source") == "Custom question"


def render_metric_cards(metrics: dict[str, Any], columns: int = 4) -> None:
    render_kpi_grid(metrics, columns=columns)


def render_list(title: str, items: list[Any]) -> None:
    if not isinstance(items, list) or not items:
        return

    st.markdown(f"**{title}**")

    for item in items:
        st.markdown(f"- {humanize(item)}")


def render_executive_summary(payload: dict[str, Any]) -> None:
    executive = payload.get("executive_summary", {})
    parsed_report = payload.get("_parsed_report", {}) or {}

    st.markdown('<div class="section-title">Executive Summary</div>', unsafe_allow_html=True)
    st.markdown(f"### {get_clean_headline(payload)}")

    metrics = {
        "decision": payload.get("decision") or parsed_report.get("status"),
        "intent": payload.get("detected_intent"),
        "partner_status": payload.get("partner_review_status"),
        "booking_score": executive.get("booking_score"),
    }

    render_kpi_grid(metrics, columns=4)


def render_agent_answer(payload: dict[str, Any]) -> None:
    st.subheader("Backend Answer")

    smart_answer = payload.get("_smart_answer", {}) or {}
    answer_text = smart_answer.get("answer") or build_frontend_answer(payload)
    decision = str(payload.get("decision") or "").lower()

    if "critical" in decision:
        answer_class = "bad"
    elif "need" in decision or "missing" in decision or "review" in decision:
        answer_class = "warn"
    else:
        answer_class = "good"

    st.markdown(
        f'<div class="answer-card {answer_class}">{esc_html(answer_text)}</div>',
        unsafe_allow_html=True,
    )

    if smart_answer:
        mode = smart_answer.get("mode")
        provider = smart_answer.get("provider")
        model = smart_answer.get("model")
        status = smart_answer.get("status")

        label = f"Answer mode: {humanize(mode)}"

        if provider:
            label += f" ? Provider: {humanize(provider)}"

        if model:
            label += f" ? Model: {model}"

        if status:
            label += f" ? Status: {humanize(status)}"

        st.caption(label)

        if smart_answer.get("error"):
            with st.expander("Smart answer error details", expanded=False):
                st.code(str(smart_answer.get("error")))

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

    if is_custom_question_payload(payload):
        st.caption(
            "This is the first stage for a custom question. If suppliers are not shortlisted here, logistics, "
            "booking readiness, and partner review cannot be completed yet."
        )

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

    if has_displayable_metrics(metrics):
        render_metric_cards(metrics, columns=4)
    else:
        render_empty_state(
            "No procurement metrics returned",
            "The backend did not return structured procurement metrics for this run.",
        )

    selected_suppliers = parsed_report.get("selected_suppliers")
    shortlisted = parsed_report.get("shortlisted_supplier_options")

    if selected_suppliers == 0 or shortlisted == 0:
        st.warning(
            "No suppliers were shortlisted. The next stage cannot create a shipment plan until at least one "
            "supplier/item option is selected."
        )

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
        render_empty_state(
            "No review sections available",
            "This run did not return structured review sections. For custom questions, this usually means only the first procurement step ran.",
        )
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


def classify_action_item(item: Any) -> str:
    text = str(item or "").lower()

    if any(word in text for word in ["incoterm", "trade term", "exw", "fob", "cif", "dap", "ddp"]):
        return "Trade Terms"

    if any(word in text for word in ["invoice", "packing list", "bill of lading", "airway", "certificate", "document"]):
        return "Documents"

    if any(word in text for word in ["freight", "insurance", "duty", "tax", "landed cost", "cost"]):
        return "Cost Inputs"

    if any(word in text for word in ["risk", "fragile", "heavy", "stack", "cargo", "dimensions", "weight"]):
        return "Cargo & Risk"

    if any(word in text for word in ["partner", "compliance", "trader", "finance"]):
        return "Partner Review"

    return "Commercial Follow-up"


def dedupe_items(items: list[Any], limit: int = 8) -> list[str]:
    cleaned = []
    seen = set()

    for item in items:
        value = humanize(item).strip()
        key = value.lower()

        if not value or key in seen:
            continue

        seen.add(key)
        cleaned.append(value)

        if len(cleaned) >= limit:
            break

    return cleaned


def render_action_cards(groups: dict[str, list[Any]]) -> None:
    cards = []

    preferred_order = [
        "Trade Terms",
        "Cost Inputs",
        "Documents",
        "Cargo & Risk",
        "Partner Review",
        "Commercial Follow-up",
    ]

    for title in preferred_order:
        items = dedupe_items(groups.get(title, []), limit=7)

        if not items:
            continue

        bullets = "".join(f"<li>{esc_html(item)}</li>" for item in items)
        cards.append(
            f'<div class="action-card"><div class="action-card-title">{esc_html(title)}</div><ul>{bullets}</ul></div>'
        )

    if not cards:
        render_empty_state(
            "No action items available",
            "The backend did not return structured next steps for this run.",
        )
        return

    st.markdown(
        f'<div class="action-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def render_booking_and_actions(payload: dict[str, Any]) -> None:
    booking = payload.get("booking_readiness", {})
    action_plan = payload.get("action_plan", {})

    st.markdown('<div class="section-title">Booking Readiness & Action Plan</div>', unsafe_allow_html=True)

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

    has_booking = has_displayable_metrics(metrics)

    all_action_items = []
    all_action_items.extend(booking.get("missing_information", []) or [])
    all_action_items.extend(booking.get("review_items", []) or [])
    all_action_items.extend(action_plan.get("before_booking", []) or [])
    all_action_items.extend(action_plan.get("partner_steps", []) or [])
    all_action_items.extend(action_plan.get("user_questions", []) or [])

    if not has_booking and not all_action_items:
        if is_custom_question_payload(payload):
            render_empty_state(
                "Booking readiness is not available for this run",
                "The backend only reached the procurement stage. Booking readiness needs selected supplier items, "
                "logistics metrics, documents, and partner review outputs.",
                [
                    "Shortlist or select supplier options first.",
                    "Provide origin, destination, Incoterm, item dimensions, and item weights.",
                    "Run logistics planning after procurement has usable item data.",
                    "Run partner review after logistics and compliance data exist.",
                ],
            )
        else:
            render_empty_state(
                "Booking readiness not returned",
                "No booking readiness object was returned in this payload.",
            )
        return

    if has_booking:
        render_kpi_grid(metrics, columns=5)

    grouped: dict[str, list[Any]] = {}

    for item in all_action_items:
        group = classify_action_item(item)
        grouped.setdefault(group, []).append(item)

    if grouped:
        st.markdown('<div class="section-caption">Grouped next steps before booking.</div>', unsafe_allow_html=True)
        render_action_cards(grouped)


def render_payload(payload: dict[str, Any]) -> None:
    render_executive_summary(payload)

    render_stage_tracker(payload)

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

        backend_validation = payload.get("backend_validation", {})

        if has_displayable_metrics(backend_validation):
            render_metric_cards(backend_validation, columns=3)
        else:
            render_empty_state(
                "Backend validation details are not available",
                "This custom text response did not return a structured backend validation block. "
                "Use the raw payload tab for debugging, or run the sample shopping flow for the full contract-validated payload.",
            )

    with procurement_tab:
        render_procurement_summary(payload)

    with logistics_tab:
        st.subheader("Logistics Metrics")

        logistics_metrics = payload.get("logistics_metrics", {})
        logistics_visualizer = payload.get("logistics_visualizer", {})

        if has_displayable_metrics(logistics_metrics):
            render_metric_cards(logistics_metrics, columns=4)
            st.divider()
            render_logistics_visualizer(logistics_visualizer)
        else:
            render_empty_state(
                "Logistics has not run for this custom question",
                "No container, CBM, weight, routing, or visualizer data can be shown until procurement produces usable selected items.",
                [
                    "Select supplier/item options.",
                    "Provide dimensions and unit weights.",
                    "Provide origin, destination, and Incoterm.",
                    "Then run the logistics agent.",
                ],
            )

            if logistics_visualizer:
                st.divider()
                render_logistics_visualizer(logistics_visualizer)

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

    inject_app_styles()

    if "active_payload" not in st.session_state:
        with st.spinner("Loading sample shopping request..."):
            st.session_state.active_payload = get_sample_shopping_payload()
            st.session_state.active_source = "Sample shopping request"
            st.session_state.active_question = ""

    st.markdown('<div class="section-title">Ask a Custom Question</div>', unsafe_allow_html=True)

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

    render_app_header(payload)

    render_payload(payload)


if __name__ == "__main__":
    main()
