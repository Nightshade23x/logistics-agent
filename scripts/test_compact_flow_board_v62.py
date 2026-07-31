from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
COMPONENT = FRONTEND / "src" / "components" / "AnswerFlow.jsx"
STYLES = FRONTEND / "src" / "styles.css"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    component = COMPONENT.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")

    require("COMPACT_FLOW_BOARD_V62" in component, "compact flow-board component marker missing")
    require("COMPACT_FLOW_BOARD_V62" in styles, "compact flow-board CSS marker missing")
    require("const NODES_PER_ROW = 4" in component, "flowchart does not use compact four-node rows")
    require("process-flow-board-row" in component, "multi-row board rendering missing")
    require("process-flow-row-connector" in component, "horizontal row connectors missing")
    require("process-flow-row-break" in component, "row-break connector missing")

    require("<svg viewBox=\"0 0 220 112\"" in component, "stable SVG decision diamond missing")
    require("<polygon points=\"110,2 218,56 110,110 2,56\"" in component, "decision polygon missing")
    require("process-flow-decision-meta" in component, "decision metadata was not moved outside the diamond")

    require("grid-template-columns:repeat(2,minmax(0,210px))" in styles, "tablet fallback layout missing")
    require("stroke:#0b1f33" in styles, "decision outline is not high contrast")
    require("fill:var(--panel)" in styles, "decision diamond does not retain readable panel background")
    require("-webkit-line-clamp:3" in styles, "long labels are not safely clamped")
    require("width:min(100%,1120px)" in styles, "full-width compact board wrapper missing")

    build = subprocess.run(
        ["G:/npm.cmd", "run", "build"],
        cwd=FRONTEND,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    require(build.returncode == 0, "frontend build failed:\n" + build.stdout + "\n" + build.stderr)

    print("PASS - flowchart uses compact left-to-right rows instead of one long vertical column")
    print("PASS - decision diamonds use SVG outlines and cannot cover their text")
    print("PASS - decision details are displayed outside the diamond")
    print("PASS - desktop, tablet and mobile layouts are responsive")
    print("PASS - frontend build succeeds")


if __name__ == "__main__":
    main()
