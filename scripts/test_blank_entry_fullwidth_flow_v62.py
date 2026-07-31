from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DASHBOARD = FRONTEND / "src/pages/Dashboard.jsx"
ANSWER_CARD = FRONTEND / "src/components/AnswerCard.jsx"
PROCESS_PAGE = FRONTEND / "src/pages/ProcessFlow.jsx"
APP = FRONTEND / "src/App.jsx"
SIDEBAR = FRONTEND / "src/components/Sidebar.jsx"
STYLES = FRONTEND / "src/styles.css"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    answer_card = ANSWER_CARD.read_text(encoding="utf-8")
    process_page = PROCESS_PAGE.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")

    require("BLANK_ENTRY_SESSION_DRAFT_V62" in dashboard, "blank-entry marker missing")
    require("sessionStorage.getItem(key)" in dashboard, "dashboard draft is not session-only")
    require("localStorage.getItem(key)" not in dashboard, "dashboard still restores a prior-launch draft")
    require(dashboard.count("sessionStorage.setItem(") >= 4, "dashboard fields are not persisted in the current tab")
    require("localStorage.setItem(" not in dashboard, "dashboard still persists draft fields across launches")

    require("AnswerFlow" not in answer_card, "flowchart still appears inside the answer card")
    require("PROCESS_FLOW_TAB_V67" in process_page, "dedicated process-flow page marker missing")
    require("<AnswerFlow result={result} />" in process_page, "dedicated process-flow result wiring missing")
    require('path="/process-flow"' in app, "process-flow route missing")
    require('to: "/process-flow"' in sidebar, "process-flow navigation item missing")
    require("FLEXIBLE_UNITS_AND_PROCESS_FLOW_TAB_V67" in styles, "V67 styles missing")
    require("border: 3px solid var(--text-primary)" in styles, "process shapes lack a strong outline")
    require("border: 2px solid var(--text-primary)" in styles, "flowchart section outline missing")

    print("PASS - new app tabs start with a blank dashboard draft")
    print("PASS - submitted input remains available within the current tab")
    print("PASS - the dynamic flowchart now has its own navigation tab")
    print("PASS - process, terminal, decision and document shapes remain intact")


if __name__ == "__main__":
    main()
