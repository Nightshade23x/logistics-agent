from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backend_service import process_json_file_request
from app.compact_frontend_payload import build_compact_frontend_payload


OUTPUT_DIR = ROOT / "demo_outputs"
OUTPUT_PATH = OUTPUT_DIR / "frontend_demo.html"
SAMPLE_REQUEST = ROOT / "data" / "suppliers" / "sample_shopping_request.json"


def esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def display_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, (int, float)):
        return str(value)

    text = str(value).strip()

    replacements = {
        "cbm": "CBM",
        "kg": "kg",
        "fcl": "FCL",
        "lcl": "LCL",
        "usa": "USA",
        "usd": "USD",
        "ai": "AI",
        "id": "ID",
    }

    text = text.replace("_", " ").replace("-", " ")
    words = []

    for word in text.split():
        lowered = word.lower()
        words.append(replacements.get(lowered, word.capitalize()))

    return " ".join(words)


def display_key(value: Any) -> str:
    return display_value(value)


def esc_display(value: Any) -> str:
    return esc(display_value(value))


def status_class(status: Any) -> str:
    text = str(status or "").lower()

    if "ready" in text and "not" not in text and "review" not in text:
        return "status-good"

    if "clear" in text or text == "available":
        return "status-good"

    if "review" in text or "missing" in text or "not_configured" in text:
        return "status-warn"

    if "critical" in text or "blocked" in text or "failed" in text:
        return "status-bad"

    return "status-neutral"


def render_badge(label: Any) -> str:
    return f'<span class="badge {status_class(label)}">{esc_display(label)}</span>'


def render_metric_grid(metrics: dict[str, Any]) -> str:
    if not isinstance(metrics, dict) or not metrics:
        return ""

    cards = []

    for key, value in metrics.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)

        cards.append(
            f"""
            <div class="metric">
                <div class="metric-label">{esc(display_key(key))}</div>
                <div class="metric-value">{esc_display(value)}</div>
            </div>
            """
        )

    return f'<div class="metric-grid">{"".join(cards)}</div>'


def render_list(items: list[Any], class_name: str = "list") -> str:
    if not isinstance(items, list) or not items:
        return ""

    rows = []

    for item in items:
        rows.append(f"<li>{esc_display(item)}</li>")

    return f'<ul class="{class_name}">{"".join(rows)}</ul>'


def render_ui_sections(sections: list[dict[str, Any]]) -> str:
    if not isinstance(sections, list):
        return ""

    cards = []

    for section in sections:
        if not isinstance(section, dict):
            continue

        cards.append(
            f"""
            <section class="card">
                <div class="card-header">
                    <h2>{esc(section.get("title"))}</h2>
                    {render_badge(section.get("status"))}
                </div>
                <p class="summary">{esc_display(section.get("summary"))}</p>
                {render_metric_grid(section.get("metrics", {}))}
                {render_list(section.get("bullets", []), "bullets")}
                {render_list(section.get("actions", []), "actions")}
            </section>
            """
        )

    return "\n".join(cards)


def render_container_visualizer(visualizer: dict[str, Any]) -> str:
    if not isinstance(visualizer, dict) or not visualizer:
        return ""

    container = visualizer.get("container", {})
    cargo_mix = visualizer.get("cargo_mix", [])
    zone_layout = visualizer.get("zone_layout", [])
    loading_sequence = visualizer.get("loading_sequence", [])
    fit_check = visualizer.get("fit_check", {})

    utilization = container.get("utilization_percent") or 0

    try:
        utilization_float = max(0.0, min(100.0, float(utilization)))
    except Exception:
        utilization_float = 0.0

    cargo_rows = []

    for item in cargo_mix:
        if not isinstance(item, dict):
            continue

        tags = item.get("category_tags", [])
        tag_html = " ".join(f'<span class="tag">{esc_display(tag)}</span>' for tag in tags)

        cargo_rows.append(
            f"""
            <tr>
                <td>{esc_display(item.get("item_name"))}</td>
                <td>{esc_display(item.get("quantity"))}</td>
                <td>{esc_display(item.get("total_cbm"))}</td>
                <td>{esc_display(item.get("total_weight_kg"))}</td>
                <td>{tag_html}</td>
            </tr>
            """
        )

    zone_cards = []

    for zone in zone_layout:
        if not isinstance(zone, dict):
            continue

        item_chips = []

        for item in zone.get("items", []):
            if not isinstance(item, dict):
                continue

            item_chips.append(
                f"""
                <div class="zone-item">
                    <strong>{esc_display(item.get("item_name"))}</strong>
                    <span>x {esc_display(item.get("quantity"))}</span>
                    <small>Step {esc_display(item.get("sequence_number"))}</small>
                </div>
                """
            )

        zone_cards.append(
            f"""
            <div class="zone-card">
                <h3>{esc_display(zone.get("zone_name"))}</h3>
                <p>{esc_display(zone.get("description"))}</p>
                <div class="zone-items">
                    {"".join(item_chips)}
                </div>
            </div>
            """
        )

    sequence_rows = []

    for step in loading_sequence:
        if not isinstance(step, dict):
            continue

        sequence_rows.append(
            f"""
            <li>
                <strong>Step {esc_display(step.get("sequence_number"))}: {esc_display(step.get("item_name"))} x {esc_display(step.get("quantity"))}</strong>
                <br>
                <span>{esc_display(step.get("suggested_zone"))}</span>
                <br>
                <small>{esc_display(step.get("reason"))}</small>
            </li>
            """
        )

    return f"""
    <section class="card visualizer-card">
        <div class="card-header">
            <h2>Logistics Visualizer</h2>
            {render_badge(visualizer.get("status"))}
        </div>

        <div class="visual-grid">
            <div>
                <h3>Container</h3>
                {render_metric_grid(container)}
            </div>

            <div>
                <h3>Utilization</h3>
                <div class="progress">
                    <div class="progress-fill" style="width: {utilization_float}%"></div>
                </div>
                <p class="summary">{esc_display(utilization)}% of safe/selected planning capacity used.</p>

                <h3>Fit Check</h3>
                {render_badge(fit_check.get("status"))}
                {render_list(fit_check.get("warnings", []), "bullets")}
                {render_list(fit_check.get("recommendations", []), "actions")}
            </div>
        </div>

        <h3>Cargo Mix</h3>
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Total CBM</th>
                    <th>Total Weight KG</th>
                    <th>Tags</th>
                </tr>
            </thead>
            <tbody>
                {"".join(cargo_rows)}
            </tbody>
        </table>

        <h3>Zone Layout</h3>
        <div class="zone-grid">
            {"".join(zone_cards)}
        </div>

        <h3>Loading Sequence</h3>
        <ol class="sequence">
            {"".join(sequence_rows)}
        </ol>
    </section>
    """


def render_html(payload: dict[str, Any]) -> str:
    executive = payload.get("executive_summary", {})
    booking = payload.get("booking_readiness", {})
    final_answer = payload.get("final_answer", {})
    visualizer = payload.get("logistics_visualizer", {})

    title = executive.get("headline") or final_answer.get("headline") or "Logistics Agent Demo"

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Logistics Agent Frontend Demo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {{
            --bg: #f5f7fb;
            --card: #ffffff;
            --text: #1f2937;
            --muted: #6b7280;
            --border: #e5e7eb;
            --good: #0f766e;
            --warn: #b45309;
            --bad: #b91c1c;
            --neutral: #374151;
            --accent: #2563eb;
        }}

        body {{
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: Arial, Helvetica, sans-serif;
            line-height: 1.5;
        }}

        .page {{
            max-width: 1180px;
            margin: 0 auto;
            padding: 32px 20px 60px;
        }}

        .hero {{
            background: linear-gradient(135deg, #0f172a, #1d4ed8);
            color: white;
            padding: 32px;
            border-radius: 22px;
            margin-bottom: 24px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18);
        }}

        .hero h1 {{
            margin: 0 0 12px;
            font-size: 32px;
        }}

        .hero p {{
            margin: 0;
            max-width: 850px;
            color: #dbeafe;
        }}

        .top-badges {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 18px;
        }}

        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 22px;
            margin-bottom: 18px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        }}

        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 10px;
        }}

        .card h2 {{
            margin: 0;
            font-size: 21px;
        }}

        .card h3 {{
            margin: 20px 0 10px;
            font-size: 16px;
        }}

        .summary {{
            color: var(--muted);
            margin: 8px 0 14px;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
            background: #eef2ff;
            color: var(--neutral);
        }}

        .status-good {{
            background: #ccfbf1;
            color: var(--good);
        }}

        .status-warn {{
            background: #fef3c7;
            color: var(--warn);
        }}

        .status-bad {{
            background: #fee2e2;
            color: var(--bad);
        }}

        .status-neutral {{
            background: #e5e7eb;
            color: var(--neutral);
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 12px;
            margin: 14px 0;
        }}

        .metric {{
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 12px;
            background: #fafafa;
        }}

        .metric-label {{
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 4px;
        }}

        .metric-value {{
            font-weight: 700;
            word-break: break-word;
        }}

        .bullets li {{
            margin-bottom: 6px;
        }}

        .actions li {{
            margin-bottom: 6px;
        }}

        .actions li::marker {{
            color: var(--accent);
        }}

        .visualizer-card {{
            border-color: #bfdbfe;
        }}

        .visual-grid {{
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 18px;
        }}

        .progress {{
            width: 100%;
            height: 22px;
            border-radius: 999px;
            background: #e5e7eb;
            overflow: hidden;
            border: 1px solid var(--border);
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #22c55e, #f59e0b);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
        }}

        th, td {{
            border-bottom: 1px solid var(--border);
            text-align: left;
            padding: 10px;
            vertical-align: top;
        }}

        th {{
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: .04em;
        }}

        .tag {{
            display: inline-block;
            padding: 4px 8px;
            background: #eff6ff;
            color: #1d4ed8;
            border-radius: 999px;
            font-size: 12px;
            margin: 2px;
        }}

        .zone-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 12px;
        }}

        .zone-card {{
            border: 1px dashed #93c5fd;
            border-radius: 16px;
            padding: 14px;
            background: #eff6ff;
        }}

        .zone-card h3 {{
            margin-top: 0;
        }}

        .zone-item {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            background: white;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 10px;
            margin-top: 8px;
        }}

        .sequence li {{
            margin-bottom: 12px;
        }}

        .footer {{
            text-align: center;
            color: var(--muted);
            margin-top: 30px;
            font-size: 13px;
        }}

        @media (max-width: 760px) {{
            .visual-grid {{
                grid-template-columns: 1fr;
            }}

            .card-header {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .hero {{
                padding: 24px;
            }}
        }}
    </style>
</head>
<body>
    <main class="page">
        <section class="hero">
            <h1>{esc_display(title)}</h1>
            <p>{esc_display(final_answer.get("answer_text") or payload.get("short_answer"))}</p>
            <div class="top-badges">
                {render_badge("Decision: " + display_value(payload.get("decision")))}
                {render_badge("Intent: " + display_value(payload.get("detected_intent")))}
                {render_badge("Partner: " + display_value(payload.get("partner_review_status")))}
                {render_badge("Contract Valid: " + display_value(payload.get("backend_validation", {}).get("response_contract_valid")))}
            </div>
        </section>

        <section class="card">
            <div class="card-header">
                <h2>Executive Summary</h2>
                {render_badge(executive.get("status"))}
            </div>
            {render_metric_grid({
                "decision": payload.get("decision"),
                "ready_for_first_pass": executive.get("ready_for_first_pass"),
                "ready_for_booking": executive.get("ready_for_booking"),
                "booking_score": executive.get("booking_score"),
                "next_gate": executive.get("next_gate"),
            })}
        </section>

        <section class="card">
            <div class="card-header">
                <h2>Logistics Metrics</h2>
                {render_badge(payload.get("logistics_metrics", {}).get("risk_level"))}
            </div>
            {render_metric_grid(payload.get("logistics_metrics", {}))}
        </section>

        {render_container_visualizer(visualizer)}

        <section class="card">
            <div class="card-header">
                <h2>Booking Readiness</h2>
                {render_badge(booking.get("status"))}
            </div>
            {render_metric_grid({
                "score": booking.get("score"),
                "ready_for_first_pass": booking.get("ready_for_first_pass"),
                "ready_for_booking": booking.get("ready_for_booking"),
                "next_gate": booking.get("next_gate"),
            })}
            <h3>Missing Information</h3>
            {render_list(booking.get("missing_information", []), "bullets")}
            <h3>Next Steps</h3>
            {render_list(booking.get("next_steps", []), "actions")}
        </section>

        {render_ui_sections(payload.get("ui_sections", []))}

        <section class="card">
            <div class="card-header">
                <h2>Backend Validation</h2>
                {render_badge(payload.get("backend_validation", {}).get("response_contract_valid"))}
            </div>
            {render_metric_grid(payload.get("backend_validation", {}))}
        </section>

        <div class="footer">
            Generated from compact frontend payload. Standalone demo mode does not require live partner services.
        </div>
    </main>
</body>
</html>
"""


def main() -> None:
    os.environ.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    OUTPUT_DIR.mkdir(exist_ok=True)

    full_payload = process_json_file_request(SAMPLE_REQUEST)
    compact_payload = build_compact_frontend_payload(full_payload)

    html_text = render_html(compact_payload)
    OUTPUT_PATH.write_text(html_text, encoding="utf-8")

    print(f"Exported static frontend demo to: {OUTPUT_PATH}")
    print("")
    print("Summary:")
    print(f"- decision: {compact_payload.get('decision')}")
    print(f"- intent: {compact_payload.get('detected_intent')}")
    print(f"- partner_review_status: {compact_payload.get('partner_review_status')}")
    print(f"- logistics_visualizer: {bool(compact_payload.get('logistics_visualizer'))}")
    print(f"- backend_contract_valid: {compact_payload.get('backend_validation', {}).get('response_contract_valid')}")


if __name__ == "__main__":
    main()
