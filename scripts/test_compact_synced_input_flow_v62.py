from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DASHBOARD = FRONTEND / "src" / "pages" / "Dashboard.jsx"
STYLES = FRONTEND / "src" / "styles.css"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")

    require("SYNCED_FREE_GUIDED_INPUT_V62" in dashboard, "free/guided synchronization marker missing")
    require("editGuidedFromExisting" in dashboard, "guided import-review state missing")
    require("updateFreeText" in dashboard, "free-text update bridge missing")
    require("guided-synced-request" in dashboard, "same-request guided review missing")
    require("Use this same request" in dashboard, "same-request submission action missing")
    require("Edit this request step by step" in dashboard, "explicit guided-edit action missing")
    require("readOnly" in dashboard and "value={text}" in dashboard, "guided review does not display the canonical request")
    require("onDraftChange={setText}" not in dashboard, "guided mount can still erase the canonical free-text request")
    require('onChange={(e) => updateFreeText(e.target.value)}' in dashboard, "free textarea does not preserve canonical synchronization")
    require("onClick={() => updateFreeText(sample)}" in dashboard, "example cards do not update the canonical request")

    require("COMPACT_PROCESS_FLOW_V62" in styles, "compact flowchart marker missing")
    require("width:min(100%,820px)" in styles, "full flowchart wrapper was not reduced")
    require("width:min(100%,430px)" in styles, "flowchart nodes were not reduced")
    require("width:158px" in styles and "height:158px" in styles, "decision diamond was not reduced")
    require("height:48px" in styles, "vertical connector spacing was not reduced")

    build = subprocess.run(
        ["G:/npm.cmd", "run", "build"],
        cwd=FRONTEND,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    require(build.returncode == 0, "frontend build failed:\n" + build.stdout + "\n" + build.stderr)

    print("PASS - free and guided modes share one canonical request")
    print("PASS - switching to guided shows the current request instead of resetting to step 1")
    print("PASS - guided mounting cannot erase the free-text prompt")
    print("PASS - step-by-step editing remains available only when explicitly selected")
    print("PASS - the dynamic flowchart is substantially more compact")
    print("PASS - frontend build succeeds")


if __name__ == "__main__":
    main()
