from __future__ import annotations

import html
import re
from typing import Any


def humanize_workflow(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"

    if value is None:
        return "Not available"

    text = str(value).strip().replace("_", " ")

    if not text:
        return "Not available"

    return text[:1].upper() + text[1:]


def active_request_text() -> str:
    try:
        import streamlit as st

        values = [
            st.session_state.get("active_question", ""),
            st.session_state.get("last_run_message", ""),
        ]

        return "\n".join(str(value) for value in values if value)
    except Exception:
        return ""


def infer_known_request_fields(request_text: str) -> dict[str, bool]:
    text = (request_text or "").lower()

    patterns = {
        "origin_country": [
            r"origin country\s*:\s*\w+",
            r"\borigin\s*:\s*\w+",
            r"\bfrom\s+india\b",
        ],
        "destination_country": [
            r"destination country\s*:\s*\w+",
            r"\bdestination\s*:\s*\w+",
            r"\bto\s+(usa|united states|zambia|finland|india)\b",
        ],
        "incoterm": [
            r"incoterm\s*/?\s*trade term\s*:\s*\w+",
            r"\bincoterm\s*:\s*\w+",
            r"\btrade term\s*:\s*\w+",
            r"\b(exw|fob|cif|dap|ddp)\b",
        ],
        "item_dimensions": [
            r"item dimensions\s*:",
            r"\bdimensions\s*:",
            r"\d+\s*x\s*\d+\s*x\s*\d+\s*cm",
        ],
        "item_weights": [
            r"item weights\s*:",
            r"\bweights\s*:",
            r"\d+\s*kg\s+each",
        ],
        "freight_quote_usd": [
            r"freight quote\s*:",
            r"freight quote usd\s*:",
        ],
        "insurance_premium_usd": [
            r"insurance premium\s*:",
            r"insurance premium usd\s*:",
        ],
        "duty_rate_percent": [
            r"duty rate\s*:",
            r"duty rate percent\s*:",
        ],
        "import_tax_rate_percent": [
            r"import tax rate\s*:",
            r"import tax rate percent\s*:",
        ],
    }

    return {
        field: any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in field_patterns)
        for field, field_patterns in patterns.items()
    }


def collect_missing_items_from_payload(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []

    direct_missing = payload.get("missing_information")

    if isinstance(direct_missing, list):
        missing.extend(str(item) for item in direct_missing if item)
    elif direct_missing:
        missing.append(str(direct_missing))

    booking = payload.get("booking_readiness")

    if isinstance(booking, dict):
        for key in ["missing_information", "missing_inputs", "required_inputs", "open_items", "next_steps"]:
            value = booking.get(key)

            if isinstance(value, list):
                missing.extend(str(item) for item in value if item)
            elif value:
                missing.append(str(value))

    cleaned: list[str] = []
    seen = set()

    for item in missing:
        readable = humanize_workflow(item)

        if readable.lower() in seen:
            continue

        seen.add(readable.lower())
        cleaned.append(readable)

    return cleaned[:20]


def missing_text_to_field_ids(missing_items: list[str]) -> set[str]:
    fields: set[str] = set()

    for raw_item in missing_items:
        item = str(raw_item).lower()

        if "origin" in item:
            fields.add("origin_country")
        if "destination" in item:
            fields.add("destination_country")
        if "incoterm" in item or "trade term" in item or "shipping term" in item:
            fields.add("incoterm")
        if "dimension" in item or "length" in item or "width" in item or "height" in item:
            fields.add("item_dimensions")
        if "weight" in item or "kg" in item:
            fields.add("item_weights")
        if "freight" in item and "quote" in item:
            fields.add("freight_quote_usd")
        if "insurance" in item:
            fields.add("insurance_premium_usd")
        if "duty" in item:
            fields.add("duty_rate_percent")
        if "import tax" in item or "tax rate" in item:
            fields.add("import_tax_rate_percent")

    return fields


def user_fillable_missing_fields(
    payload: dict[str, Any],
    request_text: str | None = None,
    missing_items: list[str] | None = None,
) -> list[str]:
    known = infer_known_request_fields(request_text if request_text is not None else active_request_text())
    missing_items = missing_items if missing_items is not None else collect_missing_items_from_payload(payload)
    detected_missing_fields = missing_text_to_field_ids(missing_items)

    field_order = [
        "origin_country",
        "destination_country",
        "incoterm",
        "item_dimensions",
        "item_weights",
        "freight_quote_usd",
        "insurance_premium_usd",
        "duty_rate_percent",
        "import_tax_rate_percent",
    ]

    if detected_missing_fields:
        return [
            field
            for field in field_order
            if field in detected_missing_fields and not known.get(field, False)
        ]

    booking = payload.get("booking_readiness") if isinstance(payload.get("booking_readiness"), dict) else {}

    if booking.get("ready_for_booking") is False:
        default_review_fields = [
            "incoterm",
            "item_dimensions",
            "item_weights",
            "freight_quote_usd",
            "insurance_premium_usd",
            "duty_rate_percent",
            "import_tax_rate_percent",
        ]

        return [
            field
            for field in default_review_fields
            if not known.get(field, False)
        ]

    return []


def field_display_name(field: str) -> str:
    names = {
        "origin_country": "Origin country",
        "destination_country": "Destination country",
        "incoterm": "Incoterm / trade term",
        "item_dimensions": "Item dimensions",
        "item_weights": "Item weights",
        "freight_quote_usd": "Freight quote USD",
        "insurance_premium_usd": "Insurance premium USD",
        "duty_rate_percent": "Duty rate percent",
        "import_tax_rate_percent": "Import tax rate percent",
    }

    return names.get(field, humanize_workflow(field))


def infer_next_frontend_action(payload: dict[str, Any]) -> str:
    missing_fields = user_fillable_missing_fields(payload)
    booking = payload.get("booking_readiness") if isinstance(payload.get("booking_readiness"), dict) else {}
    partner_status = str(payload.get("partner_review_status") or "").lower()

    if missing_fields:
        labels = ", ".join(field_display_name(field) for field in missing_fields[:4])
        return f"Next: fill {labels}, then click Rerun With Added Information."

    if booking.get("ready_for_booking") is True:
        return "Next: review Procurement and Logistics, then proceed to final booking or live partner approval."

    if "not_configured" in partner_status or "not configured" in partner_status:
        return "Next: local agents are done. To test partner approval, start finance + orchestrator, enable live partner mode, then rerun."

    if "review" in str(payload.get("decision") or "").lower():
        return "Next: open Review Sections, check warnings, then decide whether more partner or document checks are needed."

    return "Next: use Guided Request Builder for a new request, or inspect the Action Center and tabs below."


def workflow_step_states(payload: dict[str, Any]) -> list[dict[str, str]]:
    agents = payload.get("agents_called") or []
    missing_fields = user_fillable_missing_fields(payload)
    booking = payload.get("booking_readiness") if isinstance(payload.get("booking_readiness"), dict) else {}

    return [
        {"label": "1. Build request", "status": "Done", "class": "done"},
        {"label": "2. Run agents", "status": "Done" if agents else "Pending", "class": "done" if agents else "pending"},
        {"label": "3. Review output", "status": "Done" if payload.get("decision") or payload.get("partner_review_status") else "Pending", "class": "done" if payload.get("decision") or payload.get("partner_review_status") else "pending"},
        {"label": "4. Fill gaps", "status": "Active" if missing_fields else "Done", "class": "active" if missing_fields else "done"},
        {"label": "5. Booking", "status": "Ready" if booking.get("ready_for_booking") is True else "Pending", "class": "done" if booking.get("ready_for_booking") is True else "pending"},
    ]


def render_workflow_guide(payload: dict[str, Any]) -> None:
    import html
    import streamlit.components.v1 as components

    steps = workflow_step_states(payload)

    step_html = []
    for step in steps:
        bg = {
            "done": "rgba(20,83,45,0.28)",
            "active": "rgba(120,53,15,0.28)",
            "pending": "rgba(15,23,42,0.48)",
        }.get(step["class"], "rgba(15,23,42,0.48)")

        border = {
            "done": "rgba(34,197,94,0.55)",
            "active": "rgba(245,158,11,0.70)",
            "pending": "rgba(148,163,184,0.20)",
        }.get(step["class"], "rgba(148,163,184,0.20)")

        step_html.append(
            f"""
            <div style='border:1px solid {border}; background:{bg}; border-radius:16px; padding:13px 14px; min-height:78px;'>
                <div style='color:#f8fafc; font-size:0.92rem; font-weight:900; margin-bottom:4px;'>{html.escape(str(step["label"]))}</div>
                <div style='color:#94a3b8; font-size:0.78rem; font-weight:800; text-transform:uppercase; letter-spacing:0.04em;'>{html.escape(str(step["status"]))}</div>
            </div>
            """
        )

    next_action = infer_next_frontend_action(payload)
    next_action_text = str(next_action)

    if next_action_text.lower().startswith("next:"):
        next_action_text = next_action_text[5:].strip()


    workflow_html = f"""
    <div style='border:1px solid rgba(59,130,246,0.28); border-radius:22px; padding:18px 20px;
                background:linear-gradient(135deg, rgba(15,23,42,0.88), rgba(30,41,59,0.54));
                margin:0; font-family:Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;'>
        <div style='color:#f8fafc; font-size:1.12rem; font-weight:900; margin-bottom:8px;'>Workflow Guide</div>
        <div style='color:#cbd5e1; font-size:0.92rem; margin-bottom:16px;'>
            Use this to know where you are, what has already run, and what to do next.
        </div>
        <div style='display:grid; grid-template-columns:repeat(5, minmax(0, 1fr)); gap:12px; margin-bottom:16px;'>
            {''.join(step_html)}
        </div>
        <div style='border-left:4px solid rgba(248,113,113,0.90); border-radius:14px; padding:13px 15px;
                    background:rgba(127,29,29,0.18); color:#fee2e2; font-weight:800;'>
            Next: {html.escape(next_action_text)}
        </div>
    </div>
    """

    components.html(workflow_html, height=380, scrolling=False)

