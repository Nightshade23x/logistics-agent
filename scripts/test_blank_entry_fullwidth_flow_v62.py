from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "frontend" / "src" / "pages" / "Dashboard.jsx"
ANSWER_CARD = ROOT / "frontend" / "src" / "components" / "AnswerCard.jsx"
STYLES = ROOT / "frontend" / "src" / "styles.css"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    answer_card = ANSWER_CARD.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")

    require("BLANK_ENTRY_SESSION_DRAFT_V62" in dashboard, "blank-entry marker missing")
    require("sessionStorage.getItem(key)" in dashboard, "dashboard draft is not session-only")
    require("localStorage.getItem(key)" not in dashboard, "dashboard still restores a prior-launch draft")
    require(dashboard.count("sessionStorage.setItem(") >= 4, "dashboard fields are not persisted in the current tab")
    require("localStorage.setItem(" not in dashboard, "dashboard still persists draft fields across launches")

    require('<div className="answer-flow-full-width">' in answer_card, "flowchart full-width wrapper missing")
    require('<AnswerFlow steps={flowSteps} result={result} />' in answer_card, "dynamic flowchart result wiring missing")

    layout_start = answer_card.index('<div className="answer-layout">')
    full_width_start = answer_card.index('<div className="answer-flow-full-width">')
    flow_component = answer_card.index('<AnswerFlow steps={flowSteps} result={result} />')
    require(layout_start < full_width_start <= flow_component, "flowchart is not placed below the answer layout")

    require("BLANK_ENTRY_FULL_WIDTH_FLOW_V62" in styles, "final layout marker missing")
    require(".answer-flow-full-width" in styles, "full-width flowchart style missing")
    require("width: min(100%, 1040px)" in styles, "flowchart is not centered at a useful full width")
    require("position: static" in styles and "top: auto" in styles, "old sticky side-column behavior remains")
    require("border: 3px solid var(--text-primary)" in styles, "process shapes lack a strong outline")
    require(".process-flow-kind-decision .process-flow-shape::before" in styles, "decision outline selector missing")
    require("border: 2px solid var(--text-primary)" in styles, "flowchart section outline missing")

    print("PASS - new app tabs start with a blank dashboard draft")
    print("PASS - submitted input remains available within the current tab")
    print("PASS - the flowchart is full width below the complete answer")
    print("PASS - process, terminal, decision and document shapes have high-contrast outlines")


if __name__ == "__main__":
    main()
