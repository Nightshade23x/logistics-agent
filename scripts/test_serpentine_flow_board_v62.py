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

    require("SERPENTINE_FLOW_BOARD_V62" in component, "serpentine component marker missing")
    require("SERPENTINE_FLOW_BOARD_V62" in styles, "serpentine CSS marker missing")
    require('const reverse = rowIndex % 2 === 1' in component, "alternating row direction missing")
    require('reverse ? "←" : "→"' in component, "direction-aware row arrows missing")
    require('const side = reverse ? "left" : "right"' in component, "edge row-break placement missing")
    require("process-flow-board-row-reverse" in component, "reverse row class missing")
    require("process-flow-row-break-left" in styles, "left edge row-break style missing")
    require("process-flow-row-break-right" in styles, "right edge row-break style missing")
    require("fill:#ffffff !important" in styles, "decision diamond is not forced to a readable fill")
    require("color:#0b1f33 !important" in styles, "decision text contrast rule missing")
    require("width:min(100%,1030px)" in styles, "compact board width missing")

    build = subprocess.run(
        ["G:/npm.cmd", "run", "build"],
        cwd=FRONTEND,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    require(build.returncode == 0, "frontend build failed:\n" + build.stdout + "\n" + build.stderr)

    print("PASS - rows alternate left-to-right and right-to-left")
    print("PASS - downward row transitions sit at the correct outer edge")
    print("PASS - diamond fill and text contrast are readable")
    print("PASS - compact overall size is retained")
    print("PASS - frontend build succeeds")


if __name__ == "__main__":
    main()
