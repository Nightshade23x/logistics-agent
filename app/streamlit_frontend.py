from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from app.frontend_workflow import (
    active_request_text,
    collect_missing_items_from_payload,
    field_display_name,
    infer_known_request_fields,
    infer_next_frontend_action,
    missing_text_to_field_ids,
    render_workflow_guide,
    user_fillable_missing_fields,
    workflow_step_states,
)

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.compact_frontend_payload import build_compact_frontend_payload
from app.frontend_payload import build_frontend_payload
from app.user_agent import run_user_agent_from_files, run_user_agent_from_text
from app.smart_answer import generate_smart_answer, get_gemini_api_key, get_gemini_model


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

            .control-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 14px;
                margin: 12px 0 20px 0;
            }

            .control-card {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 18px;
                padding: 16px 18px;
                background: rgba(15, 23, 42, 0.68);
            }

            .control-title {
                color: #f8fafc;
                font-size: 0.95rem;
                font-weight: 900;
                margin-bottom: 6px;
            }

            .control-detail {
                color: #94a3b8;
                font-size: 0.84rem;
                line-height: 1.45;
            }

            .guided-builder-card {
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 20px;
                padding: 18px 20px;
                margin: 10px 0 20px 0;
                background: rgba(15, 23, 42, 0.62);
            }

            .action-center-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 14px;
                margin: 12px 0 18px 0;
            }

            .action-center-card {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 18px;
                padding: 15px 17px;
                background: rgba(2, 6, 23, 0.54);
            }

            .action-center-label {
                color: #94a3b8;
                font-size: 0.78rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 5px;
            }

            .action-center-value {
                color: #f8fafc;
                font-size: 1.02rem;
                font-weight: 900;
            }

            .next-step-box {
                border-left: 4px solid rgba(59, 130, 246, 0.85);
                border-radius: 14px;
                padding: 12px 15px;
                background: rgba(30, 64, 175, 0.13);
                margin: 8px 0;
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



# FRONTEND_PARTNER_MODE_FALLBACK_PATCH
def get_display_agents_called(payload: dict) -> list[str]:
    """Return only agents actually called by the backend.

    Important: an empty list is meaningful for booking_information / needs_more_information.
    Do not replace [] with Shopping Agent or any fallback.
    """
    if not isinstance(payload, dict):
        return []

    agents = payload.get("agents_called")
    if isinstance(agents, list):
        return agents

    raw = payload.get("_raw_user_agent_response")
    if isinstance(raw, dict):
        raw_agents = raw.get("agents_called")
        if isinstance(raw_agents, list):
            return raw_agents

    return []


def get_display_decision(payload: dict) -> str:
    """Return the user-facing decision without converting missing-info cases to review_required."""
    if not isinstance(payload, dict):
        return "review_required"

    status = payload.get("status")
    intent = payload.get("detected_intent")

    if status == "needs_more_information" or intent == "booking_information":
        return "needs_more_information"

    decision = payload.get("decision")
    if decision:
        return decision

    raw = payload.get("_raw_user_agent_response")
    if isinstance(raw, dict):
        raw_status = raw.get("status")
        raw_intent = raw.get("detected_intent")
        if raw_status == "needs_more_information" or raw_intent == "booking_information":
            return "needs_more_information"

        final_verdict = raw.get("final_verdict")
        if isinstance(final_verdict, dict) and final_verdict.get("verdict"):
            return final_verdict.get("verdict")

        if raw_status:
            return raw_status

    if status:
        return status

    return "review_required"


def get_partner_review_mode(payload: dict) -> str | None:
    """Return partner review mode even if compact payload dropped it."""
    if not isinstance(payload, dict):
        return None

    direct = payload.get("partner_review_mode")
    if direct:
        return direct

    raw = payload.get("_raw_user_agent_response")
    if isinstance(raw, dict):
        raw_direct = raw.get("partner_review_mode")
        if raw_direct:
            return raw_direct

        if raw.get("live_orchestrator_configured") is True:
            return "live_orchestrator"

        partner_review = raw.get("partner_review")
        if isinstance(partner_review, dict):
            nested_mode = partner_review.get("partner_review_mode") or partner_review.get("mode")
            if nested_mode:
                return nested_mode

            handoff = partner_review.get("handoff_payload")
            if isinstance(handoff, dict):
                handoff_mode = handoff.get("partner_review_mode") or handoff.get("mode")
                if handoff_mode:
                    return handoff_mode

    partner_review = payload.get("partner_review")
    if isinstance(partner_review, dict):
        nested_mode = partner_review.get("partner_review_mode") or partner_review.get("mode")
        if nested_mode:
            return nested_mode

        handoff = partner_review.get("handoff_payload")
        if isinstance(handoff, dict):
            handoff_mode = handoff.get("partner_review_mode") or handoff.get("mode")
            if handoff_mode:
                return handoff_mode

    if payload.get("live_orchestrator_configured") is True:
        return "live_orchestrator"

    return None


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
            render_chip("Partner Mode", get_partner_review_mode(payload)),
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
        or get_display_agents_called(payload)
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
        icon = "Pending:" if state == "done" else ("Pending:" if state == "active" else "Pending:")
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
        or "Pending:" in text
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
    """Extract item quantities for frontend debug display.

    Prefer the shared shipment text parser so frontend debug output matches the
    backend payload. Fall back to a guarded regex if the shared parser cannot
    produce items.
    """
    text = question or ""

    blocked_item_words = {
        "usd",
        "eur",
        "gbp",
        "$",
        "dollar",
        "dollars",
        "budget",
        "cost",
        "quote",
        "rate",
        "percent",
        "percentage",
        "per cent",
        "tax",
        "duty",
        "insurance",
        "premium",
        "freight",
    }

    try:
        from app.text_shipment_parser import parse_shipment_text

        parsed = parse_shipment_text(text)
        parsed_items = parsed.get("items", []) if isinstance(parsed, dict) else []

        cleaned_items: list[dict[str, str]] = []
        seen = set()

        for parsed_item in parsed_items:
            if not isinstance(parsed_item, dict):
                continue

            quantity = parsed_item.get("quantity")
            name = (
                parsed_item.get("name")
                or parsed_item.get("item")
                or parsed_item.get("product_name")
            )

            if quantity is None or not name:
                continue

            item_name = str(name).strip(" .,").lower()
            words = item_name.split()

            if not item_name:
                continue

            if item_name in blocked_item_words:
                continue

            if any(word in blocked_item_words for word in words):
                continue

            key = (str(quantity), item_name)
            if key in seen:
                continue

            seen.add(key)
            cleaned_items.append({"quantity": str(quantity), "item": item_name})

        if cleaned_items:
            return cleaned_items
    except Exception:
        pass

    # Regex fallback for older/simple prompts.
    pattern = re.compile(
        r"\b(?P<quantity>\d+)\s+(?P<item>[A-Za-z][A-Za-z0-9 /-]*?)"
        r"(?=\s+and\s+\d+\s+[A-Za-z]|\s+\d+\s+[A-Za-z]|,|\.| from | under | below | within | with | budget | avoid | prefer |$)",
        re.IGNORECASE,
    )

    items: list[dict[str, str]] = []

    for match in pattern.finditer(text):
        quantity = match.group("quantity").strip()
        item = match.group("item").strip(" .,").lower()
        item = re.sub(r"\s+and\s*$", "", item, flags=re.IGNORECASE).strip()
        words = item.split()

        if not item:
            continue

        if item in blocked_item_words:
            continue

        if any(word in blocked_item_words for word in words):
            continue

        if len(item) > 45:
            continue

        items.append({"quantity": quantity, "item": item})

    deduped: list[dict[str, str]] = []
    seen = set()

    for item in items:
        key = (item["quantity"], item["item"])

        if key in seen:
            continue

        seen.add(key)
        deduped.append(item)

    return deduped



def extract_budget(question: str) -> dict[str, Any]:
    """Extract explicit budget only.

    Do not treat arbitrary USD amounts as budget because custom trade prompts
    often contain freight quotes, insurance premiums, cargo values, duty rates,
    and tax rates.
    """
    text = question or ""

    patterns = [
        # under 12000 USD / below 12000 USD / within 12000 USD
        r"\b(?:under|below|within)\s*(?P<amount>\d+(?:\.\d+)?)\s*(?P<currency>usd|eur|gbp|\$)\b",

        # budget is 12000 USD / budget of 12000 USD / max budget 12000 USD
        r"\b(?:budget(?:\s+is)?|budget(?:\s+of)?|max(?:imum)?(?:\s+budget)?(?:\s+of)?|limit(?:\s+of)?)\s*(?P<amount>\d+(?:\.\d+)?)\s*(?P<currency>usd|eur|gbp|\$)?\b",

        # 12000 USD budget / 12000 USD limit
        r"\b(?P<amount>\d+(?:\.\d+)?)\s*(?P<currency>usd|eur|gbp|\$)\s*(?:budget|limit)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if not match:
            continue

        currency = (match.group("currency") or "USD").upper()
        if currency == "$":
            currency = "USD"

        return {
            "amount": float(match.group("amount")),
            "currency": currency,
        }

    return {}



def extract_country_list(question: str, keyword: str) -> list[str]:
    if keyword == "avoid":
        pattern = r"\bavoid\s+(Pending:P<countries>[A-Za-z ,]+Pending:)(Pending:=\.|;|$)"
    else:
        pattern = r"\b(Pending::from|prefer(Pending:: suppliers from)Pending:)\s+(Pending:P<countries>[A-Z][A-Za-z ,]+Pending:)(Pending:=\.|,| under | below | within | budget | avoid |$)"

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

    status_patterns = [
        r"Shopping Agent status:\s*(?P<value>[A-Za-z_]+)",
        r"\bStatus:\s*(?P<value>[A-Za-z_]+)",
    ]

    for pattern in status_patterns:
        match = re.search(pattern, report_text, flags=re.IGNORECASE)

        if match:
            parsed["status"] = match.group("value").strip()
            break

    selected_match = re.search(
        r"Selected suppliers:\s*(?P<value>\d+)",
        report_text,
        flags=re.IGNORECASE,
    )

    if not selected_match:
        selected_match = re.search(
            r"Selected\s+(?P<value>\d+)\s+supplier",
            report_text,
            flags=re.IGNORECASE,
        )

    supplier_options_match = re.search(
        r"Shortlisted\s*(?P<value>\d+)\s*supplier option",
        report_text,
        flags=re.IGNORECASE,
    )

    if not supplier_options_match:
        supplier_options_match = re.search(
            r"Selected\s+(?P<value>\d+)\s+supplier option",
            report_text,
            flags=re.IGNORECASE,
        )

    cost_match = re.search(
        r"Estimated (?:total )?procurement cost:\s*(?P<value>[0-9.]+)\s*USD",
        report_text,
        flags=re.IGNORECASE,
    )

    budget_match = re.search(
        r"Budget limit:\s*(?P<value>[0-9.]+)\s*USD",
        report_text,
        flags=re.IGNORECASE,
    )

    risk_match = re.search(
        r"Overall risk level:\s*(?P<value>[A-Za-z_]+)",
        report_text,
        flags=re.IGNORECASE,
    )

    destination_match = re.search(
        r"Destination country:\s*(?P<value>[A-Za-z_]+)",
        report_text,
        flags=re.IGNORECASE,
    )

    excluded_match = re.search(
        r"Excluded supplier countries:\s*\[(?P<value>[^\]]*)\]",
        report_text,
        flags=re.IGNORECASE,
    )

    if selected_match:
        parsed["selected_suppliers"] = int(selected_match.group("value"))

    if supplier_options_match:
        parsed["shortlisted_supplier_options"] = int(supplier_options_match.group("value"))

    if cost_match:
        parsed["estimated_procurement_cost_usd"] = float(cost_match.group("value"))

    if budget_match:
        parsed["budget_limit_usd"] = float(budget_match.group("value"))

    if risk_match:
        parsed["overall_risk_level"] = risk_match.group("value").strip()

    if destination_match:
        destination = destination_match.group("value").strip()
        parsed["destination_country"] = None if destination.lower() == "none" else destination

    if excluded_match:
        countries = []
        raw = excluded_match.group("value")

        for quoted_single, quoted_double in re.findall(r"'([^']+)'|\"([^\"]+)\"", raw):
            value = quoted_single or quoted_double

            if value:
                countries.append(value)

        if not countries:
            countries = [
                value.strip()
                for value in raw.split(",")
                if value.strip()
            ]

        parsed["excluded_supplier_countries"] = countries

    return parsed



def get_sample_shopping_payload() -> dict[str, Any]:
    full_payload = process_json_file_request(SAMPLE_SHOPPING_REQUEST)
    compact_payload = build_compact_frontend_payload(full_payload)
    compact_payload["_source"] = "Sample shopping request"
    return compact_payload


def get_text_payload(
    text_request: str,
    use_trained_router: bool | None = None,
) -> dict[str, Any]:
    if use_trained_router is None:
        use_trained_router = bool(st.session_state.get("use_trained_router", False))

    apply_trained_router_runtime_settings(use_trained_router)

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
    compact_payload["router_source"] = raw_response.get(
        "router_source",
        "trained_router" if use_trained_router else "rule_based",
    )
    compact_payload["trained_router_decision"] = json_safe(
        raw_response.get("trained_router_decision")
    )
    compact_payload["review_services_called"] = raw_response.get("review_services_called", [])
    compact_payload["_use_trained_router"] = use_trained_router

    if is_empty(compact_payload.get("decision")) and parsed_report.get("status"):
        compact_payload["decision"] = parsed_report["status"]

    if is_empty(compact_payload.get("detected_intent")):
        compact_payload["detected_intent"] = "shopping"

    # Preserve backend agents_called exactly; [] is meaningful for booking_information.
    if compact_payload.get("agents_called") is None:
        compact_payload["agents_called"] = []

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
    decision = humanize(get_display_decision(payload))
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
            "partner_review_service",
            "review_required",
            "needs_more_information",
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


def build_structured_run_answer(payload: dict[str, Any]) -> str:
    logistics = payload.get("logistics_metrics", {}) or {}
    booking = payload.get("booking_readiness", {}) if isinstance(payload.get("booking_readiness"), dict) else {}
    partner_status = payload.get("partner_review_status")
    agents = payload.get("agents_called") or []

    parts = []

    decision = payload.get("decision")
    if decision:
        parts.append(f"Decision: {humanize(decision)}.")

    if agents:
        parts.append("Agents called: " + ", ".join(humanize(agent) for agent in agents) + ".")

    if logistics:
        cbm = logistics.get("total_cbm") or logistics.get("cbm")
        weight = logistics.get("total_weight_kg") or logistics.get("weight_kg")
        container = logistics.get("recommended_container")
        risk = logistics.get("risk_level")

        logistics_bits = []

        if cbm:
            logistics_bits.append(f"{cbm} CBM")

        if weight:
            logistics_bits.append(f"{weight} kg")

        if container:
            logistics_bits.append(f"recommended container: {humanize(container)}")

        if risk:
            logistics_bits.append(f"risk level: {humanize(risk)}")

        if logistics_bits:
            parts.append("Logistics plan: " + ", ".join(logistics_bits) + ".")

    if partner_status:
        parts.append(f"Partner review: {humanize(partner_status)}.")

    if booking:
        ready_first_pass = booking.get("ready_for_first_pass")
        ready_booking = booking.get("ready_for_booking")
        score = booking.get("score")
        next_gate = booking.get("next_gate")

        booking_bits = []

        if score is not None:
            booking_bits.append(f"booking score {score}")

        if ready_first_pass is not None:
            booking_bits.append(f"first-pass ready: {humanize(ready_first_pass)}")

        if ready_booking is not None:
            booking_bits.append(f"ready for booking: {humanize(ready_booking)}")

        if next_gate:
            booking_bits.append(f"next gate: {humanize(next_gate)}")

        if booking_bits:
            parts.append("Booking readiness: " + ", ".join(booking_bits) + ".")

    if not parts:
        return ""

    if booking and booking.get("ready_for_booking") is False:
        parts.append(
            "This is usable for review, but it still needs the missing trade, cost, document, and risk inputs before final booking."
        )

    return " ".join(parts)


def build_frontend_answer(payload: dict[str, Any]) -> str:
    if payload.get("logistics_metrics") or payload.get("booking_readiness"):
        structured_answer = build_structured_run_answer(payload)

        if structured_answer:
            return structured_answer

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
            label += f" - Provider: {humanize(provider)}"

        if model:
            label += f" - Model: {model}"

        if status:
            label += f" - Status: {humanize(status)}"

        st.caption(label)

        if smart_answer.get("error"):
            with st.expander("Smart answer error details", expanded=False):
                st.code(str(smart_answer.get("error")))

    agents_called = get_display_agents_called(payload) or []

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

        with st.expander(f"{title} | {status}", expanded=False):
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


def build_followup_question_with_missing_info(payload: dict[str, Any], answers: dict[str, Any]) -> str:
    base_question = st.session_state.get("active_question") or DEFAULT_TEXT_REQUEST

    if st.session_state.get("active_source") in ["Full structured demo", "Initial full structured demo"]:
        base_question = (
            "I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
            "Prefer suppliers from India. Avoid China. Budget is 13000 USD."
        )

    additions = []

    for key, value in answers.items():
        if is_empty(value):
            continue

        additions.append(f"{humanize(key)}: {value}")

    if not additions:
        return base_question

    return base_question.strip() + "\n\nAdditional missing information provided:\n- " + "\n- ".join(additions)


def render_missing_information_form(payload: dict[str, Any]) -> None:
    decision_text = str(payload.get("decision") or "").lower()
    booking = payload.get("booking_readiness", {}) if isinstance(payload.get("booking_readiness"), dict) else {}

    needs_info = (
        "need" in decision_text
        or "review" in decision_text
        or booking.get("ready_for_booking") is False
        or collect_missing_information(payload)
    )

    if not needs_info:
        return

    st.markdown('<div class="section-title">Provide Missing Information</div>', unsafe_allow_html=True)
    st.caption(
        "Fill what you know, then rerun. The app will append these details to the current request and send it back through the backend agents."
    )

    with st.form("missing_information_form", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            origin_country = st.text_input("Origin country", value="India")
            destination_country = st.text_input("Destination country", value="USA")
            incoterm = st.selectbox(
                "Incoterm / trade term",
                ["", "EXW", "FOB", "CIF", "DAP", "DDP", "Other"],
            )

        with col2:
            unit_dimensions = st.text_area(
                "Item dimensions",
                placeholder="Example: TV 120x70x15 cm, scooter 180x70x110 cm, tiles carton 40x40x30 cm",
                height=95,
            )
            unit_weights = st.text_area(
                "Item weights",
                placeholder="Example: TV 18 kg each, scooter 110 kg each, tile carton 25 kg each",
                height=95,
            )

        with col3:
            freight_quote_usd = st.text_input("Freight quote USD", placeholder="Example: 1800")
            insurance_premium_usd = st.text_input("Insurance premium USD", placeholder="Example: 150")
            duty_rate_percent = st.text_input("Duty rate percent", placeholder="Example: 5")
            import_tax_rate_percent = st.text_input("Import tax rate percent", placeholder="Example: 16")

        extra_notes = st.text_area(
            "Other notes",
            placeholder="Example: fragile cargo, must arrive before 15 August, supplier quote attached later",
            height=80,
        )

        submitted = st.form_submit_button("Rerun With Added Information", type="primary")

    if submitted:
        answers = {
            "origin_country": origin_country,
            "destination_country": destination_country,
            "incoterm": incoterm,
            "unit_dimensions": unit_dimensions,
            "unit_weights": unit_weights,
            "freight_quote_usd": freight_quote_usd,
            "insurance_premium_usd": insurance_premium_usd,
            "duty_rate_percent": duty_rate_percent,
            "import_tax_rate_percent": import_tax_rate_percent,
            "extra_notes": extra_notes,
        }

        followup_question = build_followup_question_with_missing_info(payload, answers)

        apply_partner_runtime_settings(
            st.session_state.get("use_live_partner", False),
            st.session_state.get("orchestrator_url", "http://127.0.0.1:8010"),
        )

        run_frontend_flow(
            source="Custom question with added information",
            question=followup_question,
            loading_message="Rerunning backend agents with the added missing information...",
            loader=lambda: get_text_payload(followup_question),
        )

        st.rerun()


def render_payload(payload: dict[str, Any]) -> None:
    render_workflow_guide(payload)

    render_executive_summary(payload)

    render_stage_tracker(payload)

    render_agent_answer(payload)

    render_missing_information_form(payload)

    render_frontend_action_center(payload)

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


def apply_partner_runtime_settings(use_live_partner: bool, orchestrator_url: str) -> None:
    if use_live_partner and orchestrator_url.strip():
        os.environ["TRADE_ORCHESTRATOR_BASE_URL"] = orchestrator_url.strip()
        return

    os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)


def render_agent_connection_summary(use_live_partner: bool, orchestrator_url: str) -> None:
    gemini_key_loaded = bool(get_gemini_api_key())
    gemini_model = get_gemini_model()

    partner_mode = "Live orchestrator" if use_live_partner else "Standalone fallback"
    partner_detail = orchestrator_url if use_live_partner else "Partner review uses local fallback unless live URL is enabled."

    cards = [
        {
            "title": "Backend agents",
            "detail": "Shopping, logistics, document AI, booking readiness, and payload builders are local backend modules.",
        },
        {
            "title": "Gemini smart answers",
            "detail": f"{'Enabled' if gemini_key_loaded else 'Fallback only'} - Model: {gemini_model}",
        },
        {
            "title": "Partner mode",
            "detail": f"{partner_mode} - {partner_detail}",
        },
    ]

    html_cards = []

    for card in cards:
        html_cards.append(
            f'<div class="control-card"><div class="control-title">{esc_html(card["title"])}</div><div class="control-detail">{esc_html(card["detail"])}</div></div>'
        )

    st.markdown(
        f'<div class="control-grid">{"".join(html_cards)}</div>',
        unsafe_allow_html=True,
    )


def load_payload_with_spinner(label: str, loader) -> None:
    with st.spinner(label):
        st.session_state.active_payload = loader()


def apply_trained_router_runtime_settings(use_trained_router: bool) -> None:
    if use_trained_router:
        os.environ["USE_TRAINED_ROUTER"] = "1"
        return

    os.environ["USE_TRAINED_ROUTER"] = "0"


def run_live_partner_health_check(orchestrator_url: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["TRADE_ORCHESTRATOR_BASE_URL"] = orchestrator_url.strip() or "http://127.0.0.1:8010"
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, "scripts/check_live_partner_stack.py"],
        cwd=ROOT_DIR,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=90,
    )

    return {
        "returncode": result.returncode,
        "output": (result.stdout or "") + ("\n" + result.stderr if result.stderr else ""),
    }


def run_frontend_flow(
    *,
    source: str,
    question: str,
    loading_message: str,
    loader,
) -> None:
    started_at = datetime.now().strftime("%H:%M:%S")

    with st.spinner(loading_message):
        payload = loader()

    st.session_state.active_payload = payload
    st.session_state.active_source = source
    st.session_state.active_question = question
    st.session_state.last_run_message = f"{source} completed at {started_at}"
    st.session_state.last_run_agents = payload.get("agents_called") or []
    st.session_state.last_run_decision = payload.get("decision")
    st.session_state.last_run_partner_status = payload.get("partner_review_status")
    st.session_state.last_run_gemini_status = (payload.get("_smart_answer", {}) or {}).get("status")
    st.session_state.last_run_gemini_mode = (payload.get("_smart_answer", {}) or {}).get("mode")


def render_last_run_status() -> None:
    message = st.session_state.get("last_run_message")

    if not message:
        return

    st.success(message)

    trace_metrics = {
        "decision": st.session_state.get("last_run_decision"),
        "agents_called": st.session_state.get("last_run_agents"),
        "partner_status": st.session_state.get("last_run_partner_status"),
        "gemini_mode": st.session_state.get("last_run_gemini_mode"),
        "gemini_status": st.session_state.get("last_run_gemini_status"),
    }

    render_kpi_grid(trace_metrics, columns=5)


def normalize_optional_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def build_guided_request_text(data: dict[str, Any]) -> str:
    items = []

    for row in data.get("items", []):
        quantity = normalize_optional_text(row.get("quantity"))
        item = normalize_optional_text(row.get("item"))

        if quantity and item:
            items.append(f"{quantity} {item}")

    if items:
        request = "I need " + ", ".join(items) + "."
    else:
        request = "I need help planning a procurement and shipment."

    preferred_country = normalize_optional_text(data.get("preferred_supplier_country"))
    avoid_countries = normalize_optional_text(data.get("avoid_countries"))
    origin_country = normalize_optional_text(data.get("origin_country"))
    destination_country = normalize_optional_text(data.get("destination_country"))
    budget_amount = normalize_optional_text(data.get("budget_amount"))
    budget_currency = normalize_optional_text(data.get("budget_currency")) or "USD"
    incoterm = normalize_optional_text(data.get("incoterm"))
    target_date = normalize_optional_text(data.get("target_date"))
    dimensions = normalize_optional_text(data.get("dimensions"))
    weights = normalize_optional_text(data.get("weights"))
    freight_quote = normalize_optional_text(data.get("freight_quote_usd"))
    insurance = normalize_optional_text(data.get("insurance_premium_usd"))
    duty_rate = normalize_optional_text(data.get("duty_rate_percent"))
    import_tax = normalize_optional_text(data.get("import_tax_rate_percent"))
    notes = normalize_optional_text(data.get("notes"))

    additions = []

    if preferred_country:
        additions.append(f"Prefer suppliers from {preferred_country}.")

    if avoid_countries:
        additions.append(f"Avoid supplier countries: {avoid_countries}.")

    if origin_country:
        additions.append(f"Origin country: {origin_country}.")

    if destination_country:
        additions.append(f"Destination country: {destination_country}.")

    if budget_amount:
        additions.append(f"Budget is {budget_amount} {budget_currency}.")

    if incoterm:
        additions.append(f"Incoterm / trade term: {incoterm}.")

    if target_date:
        additions.append(f"Target delivery date: {target_date}.")

    if dimensions:
        additions.append(f"Item dimensions: {dimensions}.")

    if weights:
        additions.append(f"Item weights: {weights}.")

    if freight_quote:
        additions.append(f"Freight quote: {freight_quote} USD.")

    if insurance:
        additions.append(f"Insurance premium: {insurance} USD.")

    if duty_rate:
        additions.append(f"Duty rate: {duty_rate}%.")

    if import_tax:
        additions.append(f"Import tax rate: {import_tax}%.")

    if notes:
        additions.append(f"Other notes: {notes}.")

    additions.append(
        "Please recommend suppliers, estimate logistics needs, flag compliance/risk issues, and tell me what is still needed before booking."
    )

    return request + " " + " ".join(additions)


def render_guided_request_builder() -> None:
    st.markdown('<div class="section-title">Guided Request Builder</div>', unsafe_allow_html=True)
    st.caption(
        "Use this when the user does not want to write a perfect prompt. The app will turn the form into a backend request and run the agents."
    )

    with st.container(border=True):
        st.markdown("**Product lines**")

        item_col1, item_col2, item_col3 = st.columns(3)

        with item_col1:
            quantity_1 = st.text_input("Quantity 1", value="50", key="guided_qty_1")
            item_1 = st.text_input("Item 1", value="TVs", key="guided_item_1")

        with item_col2:
            quantity_2 = st.text_input("Quantity 2", value="5", key="guided_qty_2")
            item_2 = st.text_input("Item 2", value="scooters", key="guided_item_2")

        with item_col3:
            quantity_3 = st.text_input("Quantity 3", value="100", key="guided_qty_3")
            item_3 = st.text_input("Item 3", value="ceramic tiles", key="guided_item_3")

        st.markdown("**Trade and shipment details**")

        base_col1, base_col2, base_col3, base_col4 = st.columns(4)

        with base_col1:
            origin_country = st.text_input("Origin country", value="India", key="guided_origin")
            preferred_supplier_country = st.text_input("Preferred supplier country", value="India", key="guided_preferred")

        with base_col2:
            destination_country = st.text_input("Destination country", value="USA", key="guided_destination")
            avoid_countries = st.text_input("Avoid supplier countries", value="China", key="guided_avoid")

        with base_col3:
            budget_amount = st.text_input("Budget amount", value="13000", key="guided_budget")
            budget_currency = st.selectbox("Budget currency", ["USD", "EUR", "GBP"], key="guided_currency")

        with base_col4:
            incoterm = st.selectbox("Incoterm", ["", "EXW", "FOB", "CIF", "DAP", "DDP", "Other"], key="guided_incoterm")
            target_date = st.text_input("Target delivery date", placeholder="Example: 2026-08-15", key="guided_target_date")

        with st.expander("Optional details for booking readiness", expanded=False):
            detail_col1, detail_col2 = st.columns(2)

            with detail_col1:
                dimensions = st.text_area(
                    "Dimensions",
                    placeholder="Example: TV 120x70x15 cm, scooter 180x70x110 cm, tile carton 40x40x30 cm",
                    height=90,
                    key="guided_dimensions",
                )
                freight_quote_usd = st.text_input("Freight quote USD", placeholder="Example: 1800", key="guided_freight")

            with detail_col2:
                weights = st.text_area(
                    "Weights",
                    placeholder="Example: TV 18 kg each, scooter 110 kg each, tile carton 25 kg each",
                    height=90,
                    key="guided_weights",
                )
                insurance_premium_usd = st.text_input("Insurance premium USD", placeholder="Example: 150", key="guided_insurance")

            tax_col1, tax_col2 = st.columns(2)

            with tax_col1:
                duty_rate_percent = st.text_input("Duty rate percent", placeholder="Example: 5", key="guided_duty")

            with tax_col2:
                import_tax_rate_percent = st.text_input("Import tax rate percent", placeholder="Example: 16", key="guided_tax")

            notes = st.text_area(
                "Other notes",
                placeholder="Example: fragile cargo, supplier quote pending, must arrive before school term starts",
                height=80,
                key="guided_notes",
            )

        data = {
            "items": [
                {"quantity": quantity_1, "item": item_1},
                {"quantity": quantity_2, "item": item_2},
                {"quantity": quantity_3, "item": item_3},
            ],
            "origin_country": origin_country,
            "destination_country": destination_country,
            "preferred_supplier_country": preferred_supplier_country,
            "avoid_countries": avoid_countries,
            "budget_amount": budget_amount,
            "budget_currency": budget_currency,
            "incoterm": incoterm,
            "target_date": target_date,
            "dimensions": dimensions if "dimensions" in locals() else "",
            "weights": weights if "weights" in locals() else "",
            "freight_quote_usd": freight_quote_usd if "freight_quote_usd" in locals() else "",
            "insurance_premium_usd": insurance_premium_usd if "insurance_premium_usd" in locals() else "",
            "duty_rate_percent": duty_rate_percent if "duty_rate_percent" in locals() else "",
            "import_tax_rate_percent": import_tax_rate_percent if "import_tax_rate_percent" in locals() else "",
            "notes": notes if "notes" in locals() else "",
        }

        preview_text = build_guided_request_text(data)

        with st.expander("Preview backend request", expanded=False):
            st.code(preview_text, language="text")

        if st.button("Run Guided Request", type="primary", use_container_width=True, key="run_guided_request"):
            apply_partner_runtime_settings(
                st.session_state.get("use_live_partner", False),
                st.session_state.get("orchestrator_url", "http://127.0.0.1:8010"),
            )

            run_frontend_flow(
                source="Guided request",
                question=preview_text,
                loading_message="Running guided request through procurement, logistics, and review agents...",
                loader=lambda: get_text_payload(preview_text),
            )

            st.rerun()


def frontend_collect_missing_items(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []

    direct_missing = payload.get("missing_information")

    if isinstance(direct_missing, list):
        missing.extend(str(item) for item in direct_missing if not is_empty(item))
    elif not is_empty(direct_missing):
        missing.append(str(direct_missing))

    booking = payload.get("booking_readiness")

    if isinstance(booking, dict):
        for key in ["missing_information", "missing_inputs", "required_inputs", "open_items"]:
            value = booking.get(key)

            if isinstance(value, list):
                missing.extend(str(item) for item in value if not is_empty(item))
            elif not is_empty(value):
                missing.append(str(value))

    review_sections = payload.get("review_sections")

    if isinstance(review_sections, list):
        for section in review_sections:
            if not isinstance(section, dict):
                continue

            for key in ["missing_information", "missing_inputs", "next_steps", "blockers", "warnings"]:
                value = section.get(key)

                if isinstance(value, list):
                    missing.extend(str(item) for item in value if not is_empty(item))
                elif not is_empty(value):
                    missing.append(str(value))

    cleaned: list[str] = []
    seen = set()

    for item in missing:
        readable = humanize(item)

        if readable.lower() in seen:
            continue

        seen.add(readable.lower())
        cleaned.append(readable)

    return cleaned[:12]


def infer_booking_status(payload: dict[str, Any]) -> str:
    booking = payload.get("booking_readiness")

    if isinstance(booking, dict):
        ready_for_booking = booking.get("ready_for_booking")
        ready_for_first_pass = booking.get("ready_for_first_pass")

        if ready_for_booking is True:
            return "Ready For Booking"

        if ready_for_first_pass is True:
            return "Ready For Review"

    decision = str(payload.get("decision") or payload.get("status") or "").lower()

    if "critical" in decision:
        return "Critical Review Needed"

    if "need" in decision:
        return "Needs More Information"

    if "review" in decision:
        return "Review Required"

    if "ready" in decision:
        return "Ready"

    return "In Progress"


def render_frontend_action_center(payload: dict[str, Any]) -> None:
    st.markdown('<div class="section-title">Action Center</div>', unsafe_allow_html=True)

    agents = payload.get("agents_called")
    missing_items = frontend_collect_missing_items(payload)
    booking = payload.get("booking_readiness") if isinstance(payload.get("booking_readiness"), dict) else {}
    smart_answer = payload.get("_smart_answer") if isinstance(payload.get("_smart_answer"), dict) else {}

    cards = [
        {
            "label": "Booking status",
            "value": infer_booking_status(payload),
        },
        {
            "label": "Agents used",
            "value": str(len(agents)) if agents else "0",
        },
        {
            "label": "Missing items",
            "value": str(len(missing_items)),
        },
    ]

    html = []

    for card in cards:
        html.append(
            f'<div class="action-center-card"><div class="action-center-label">{esc_html(card["label"])}</div><div class="action-center-value">{esc_html(card["value"])}</div></div>'
        )

    st.markdown(
        f'<div class="action-center-grid">{"".join(html)}</div>',
        unsafe_allow_html=True,
    )

    detail_col1, detail_col2 = st.columns([1.15, 1])

    with detail_col1:
        st.markdown("**Next steps**")

        next_steps: list[str] = []

        if booking.get("next_gate"):
            next_steps.append(f"Complete next gate: {humanize(booking.get('next_gate'))}")

        if missing_items:
            next_steps.append("Fill the missing information form and rerun the request.")

        if payload.get("partner_review_status"):
            next_steps.append(f"Partner review status: {humanize(payload.get('partner_review_status'))}")

        if not next_steps:
            next_steps.append("Review the procurement and logistics tabs, then proceed with booking checks.")

        for step in next_steps[:5]:
            st.markdown(
                f'<div class="next-step-box">{esc_html(step)}</div>',
                unsafe_allow_html=True,
            )

    with detail_col2:
        st.markdown("**Runtime summary**")

        runtime_rows = {
            "Answer provider": smart_answer.get("provider") or smart_answer.get("mode") or "Not available",
            "Answer status": smart_answer.get("status") or "Not available",
            "Partner mode": "Live orchestrator" if st.session_state.get("use_live_partner") else "Standalone fallback",
            "Router source": humanize(payload.get("router_source") or "rule_based"),
            "Decision": humanize(payload.get("decision") or payload.get("status")),
        }

        st.table(
            [
                {"Field": key, "Value": humanize(value)}
                for key, value in runtime_rows.items()
            ]
        )

    if missing_items:
        st.markdown("**Missing information detected**")
        st.table(
            [
                {"No.": index + 1, "Input needed": item}
                for index, item in enumerate(missing_items)
            ]
        )


def main() -> None:
    st.set_page_config(
        page_title="Logistics Agent Frontend",
        page_icon="Pending:Pending:",
        layout="wide",
    )

    inject_app_styles()

    if "active_payload" not in st.session_state:
        run_frontend_flow(
            source="Initial full structured demo",
            question="",
            loading_message="Loading full structured demo...",
            loader=get_sample_shopping_payload,
        )

    if "use_live_partner" not in st.session_state:
        st.session_state.use_live_partner = False

    if "orchestrator_url" not in st.session_state:
        st.session_state.orchestrator_url = "http://127.0.0.1:8010"

    st.markdown('<div class="section-title">Demo Controls</div>', unsafe_allow_html=True)

    with st.container(border=True):
        mode_col, url_col, status_col = st.columns([1, 1.35, 1.15])

        with mode_col:
            if "use_trained_router" not in st.session_state:
                st.session_state.use_trained_router = False

            st.session_state.use_live_partner = st.checkbox(
                "Use live partner orchestrator",
                value=st.session_state.use_live_partner,
                help="Enable this only when Avishi's orchestrator service is running locally.",
            )

            st.session_state.use_trained_router = st.checkbox(
                "Use trained router model",
                value=st.session_state.use_trained_router,
                help="Enable the fine-tuned LoRA router for custom and guided text requests.",
            )

        with url_col:
            st.session_state.orchestrator_url = st.text_input(
                "Trade orchestrator URL",
                value=st.session_state.orchestrator_url,
                help="Usually http://127.0.0.1:8010",
            )

        with status_col:
            gemini_status = "Enabled" if get_gemini_api_key() else "Fallback only"
            st.markdown("**Gemini smart answers**")
            st.caption(f"{gemini_status} - {get_gemini_model()}")

        apply_partner_runtime_settings(
            st.session_state.use_live_partner,
            st.session_state.orchestrator_url,
        )

        if st.session_state.use_live_partner:
            st.warning(
                "Live partner mode is enabled. Risk/compliance/finance/trader should answer through the orchestrator. "
                
            )

        render_agent_connection_summary(
            st.session_state.use_live_partner,
            st.session_state.orchestrator_url,
        )

        demo_col1, demo_col2, demo_col3 = st.columns(3)

        with demo_col1:
            if st.button("Run Full Structured Demo", type="primary", use_container_width=True, key="run_full_structured_demo"):
                apply_partner_runtime_settings(
                    st.session_state.use_live_partner,
                    st.session_state.orchestrator_url,
                )
                run_frontend_flow(
                    source="Full structured demo",
                    question="",
                    loading_message="Running shopping, logistics, and partner review agents...",
                    loader=get_sample_shopping_payload,
                )

        with demo_col2:
            if st.button("Run Sample Documents", use_container_width=True, key="run_sample_documents"):
                apply_partner_runtime_settings(
                    st.session_state.use_live_partner,
                    st.session_state.orchestrator_url,
                )
                run_frontend_flow(
                    source="Sample documents",
                    question="",
                    loading_message="Running document agent flow...",
                    loader=get_document_payload,
                )

        with demo_col3:
            if st.button("Run Plain-English Demo", use_container_width=True, key="run_plain_english_demo"):
                apply_partner_runtime_settings(
                    st.session_state.use_live_partner,
                    st.session_state.orchestrator_url,
                )
                run_frontend_flow(
                    source="Plain-English demo",
                    question=DEFAULT_TEXT_REQUEST,
                    loading_message="Running plain-English request through the user agent...",
                    loader=lambda: get_text_payload(DEFAULT_TEXT_REQUEST),
                )

        check_col1, check_col2 = st.columns([1, 2])

        with check_col1:
            if st.button("Check Live Partner Stack", use_container_width=True, key="check_live_partner_stack"):
                with st.spinner("Checking finance and orchestrator services..."):
                    st.session_state.partner_health_check = run_live_partner_health_check(
                        st.session_state.orchestrator_url,
                    )

        with check_col2:
            st.caption(
                "Live partner mode needs the local finance service and orchestrator service running. "
            )

        if st.session_state.get("partner_health_check"):
            result = st.session_state.partner_health_check

            if result.get("returncode") == 0:
                st.success("Live partner check completed.")
            else:
                st.warning("Live partner check completed with warnings or failures.")

            with st.expander("Live partner check output", expanded=False):
                st.code(result.get("output", ""), language="text")

    render_guided_request_builder()

    st.markdown('<div class="section-title">Ask a Custom Question</div>', unsafe_allow_html=True)

    with st.form("custom_question_form", clear_on_submit=False):
        custom_question = st.text_area(
            "Search or ask a procurement/logistics question",
            value=st.session_state.get("active_question", ""),
            placeholder=(
                "Example: I need 50 TVs, 5 scooters, and 100 ceramic tiles. "
                "Prefer suppliers from India. Avoid China. Budget is 13000 USD."
            ),
            height=95,
        )

        submitted = st.form_submit_button("Run Custom Question", type="primary")

    if submitted:
        if not custom_question.strip():
            st.warning("Type a question first.")
        else:
            apply_partner_runtime_settings(
                st.session_state.use_live_partner,
                st.session_state.orchestrator_url,
            )
            run_frontend_flow(
                source="Custom question",
                question=custom_question.strip(),
                loading_message="Running backend user agent and Gemini smart-answer synthesis...",
                loader=lambda: get_text_payload(custom_question.strip()),
            )

    payload = st.session_state.active_payload

    render_last_run_status()

    render_app_header(payload)

    st.caption(
        f"Active run: {st.session_state.active_source} - "
        f"Partner mode: {'Live orchestrator' if st.session_state.use_live_partner else 'Standalone fallback'} - "
        f"Router: {'Trained LoRA' if st.session_state.get('use_trained_router') else 'Rule-based'} - "
        f"Gemini model: {get_gemini_model()}"
    )

    render_payload(payload)


if __name__ == "__main__":
    main()

