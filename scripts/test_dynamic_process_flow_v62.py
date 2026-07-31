from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
FLOW = FRONTEND / "src" / "utils" / "processFlow.jsx"
COMPONENT = FRONTEND / "src" / "components" / "AnswerFlow.jsx"
STYLES = FRONTEND / "src" / "styles.css"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    flow_text = FLOW.read_text(encoding="utf-8")
    component_text = COMPONENT.read_text(encoding="utf-8")
    styles_text = STYLES.read_text(encoding="utf-8")
    require("DYNAMIC_PROCESS_FLOW_V62" in flow_text, "V62 utility marker missing")
    for field in ("logistics_visualizer", "route_plan", "trade_agreement_advice", "trade_compliance_readiness", "document_requirements_advice", "landed_cost_advice", "authoritative_cargo_flags"):
        require(field in flow_text, f"structured source missing: {field}")
    require("process-flow-kind-${node.kind}" in component_text, "dynamic node-kind class is not rendered")
    require("process-flow-kind-decision" in styles_text, "decision shape style missing")
    require("process-flow-kind-document" in styles_text, "document shape style missing")
    require("process-flow-row-connector" in component_text, "horizontal flow connectors missing")
    require("process-flow-row-break" in component_text, "row-break flow connectors missing")
    require("final_answer" not in flow_text, "flow must not parse final-answer prose")

    fixtures = {
        "standard": {
            "decision": "review_required",
            "logistics_metrics": {"total_cbm": 13.2, "total_weight_kg": 3000, "readiness_status": "ready_for_review"},
            "logistics_visualizer": {"status": "available", "container": {"selected_container": "20ft Standard Container", "utilization_percent": 39.76}, "cargo_mix": [{"item_name": "textiles", "hazardous": False}]},
            "route_plan": {"applicable": True, "status": "indicative_review_required", "indicative_corridor": "New York -> Haifa"},
            "trade_agreement_advice": {"applicable": True, "agreement_exists_in_local_reference": True, "agreement_name": "U.S.-Israel Free Trade Agreement"},
            "trade_compliance_readiness": {"applicable": True, "status": "blocked"},
            "document_requirements_advice": {"applicable": True, "status": "needs_more_information", "required_documents": ["Invoice"], "conditional_documents": ["Origin declaration"]},
            "insurance_advice": {"applicable": True, "status": "review_required"},
            "landed_cost_advice": {"applicable": True, "status": "blocked", "missing_cost_inputs": ["freight"]},
            "final_verdict": {"verdict": "review_required"},
        },
        "landlocked": {"logistics_metrics": {"total_cbm": 11.2}, "route_plan": {"applicable": True, "inland_precarriage_required": True, "indicative_corridor": "Zambia -> Dar es Salaam -> Helsinki"}, "final_verdict": {"verdict": "review_required"}},
        "hazardous": {"logistics_metrics": {"total_cbm": 6.72}, "logistics_visualizer": {"status": "review_required", "cargo_mix": [{"item_name": "lithium-ion batteries", "hazardous": True, "category_tags": ["lithium_battery"]}]}, "trade_compliance_readiness": {"applicable": True, "status": "blocked"}, "document_requirements_advice": {"applicable": True}, "final_verdict": {"verdict": "review_required"}},
        "radioactive": {"logistics_metrics": {"total_cbm": 0.48}, "logistics_visualizer": {"status": "review_required", "cargo_mix": [{"item_name": "radioactive medical isotopes", "hazardous": True, "category_tags": ["radioactive"]}]}, "trade_compliance_readiness": {"applicable": True, "status": "blocked"}, "final_verdict": {"verdict": "review_required"}},
        "complete_cost": {"landed_cost_advice": {"applicable": True, "status": "calculated", "missing_cost_inputs": [], "summary": "Landed cost calculated."}, "final_verdict": {"verdict": "review_required"}},
        "incomplete": {"decision": "needs_more_information", "missing_information_count": 3, "missing_information_preview": ["quantity", "dimensions", "weight"], "final_verdict": {"verdict": "needs_more_information"}},
    }

    node = shutil.which("node.exe") or shutil.which("node")
    require(node is not None, "Node.js was not found")
    with tempfile.TemporaryDirectory() as temp:
        fixture_path = Path(temp) / "fixtures.json"
        fixture_path.write_text(json.dumps(fixtures), encoding="utf-8")
        module_path = Path(temp) / "processFlow.mjs"
        module_path.write_text(flow_text, encoding="utf-8")
        js = (
            'import fs from "node:fs"; '
            f'import {{ deriveProcessFlow }} from {json.dumps(module_path.resolve().as_uri())}; '
            'const fixtures=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); '
            'const out=Object.fromEntries(Object.entries(fixtures).map(([k,v])=>[k,deriveProcessFlow(v).map(n=>({id:n.id,kind:n.kind,label:n.label,tone:n.tone}))])); '
            'console.log(JSON.stringify(out));'
        )
        result = subprocess.run([node, "--input-type=module", "-e", js, str(fixture_path)], cwd=FRONTEND, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        require(result.returncode == 0, "Node flow derivation failed:\n" + result.stderr)
        derived = json.loads(result.stdout)

    signatures = {key: tuple(node["id"] for node in nodes) for key, nodes in derived.items()}
    require(len(set(signatures.values())) >= 5, f"Flow is not sufficiently dynamic: {signatures}")
    require("specialist" in signatures["hazardous"], "hazardous flow lacks specialist decision")
    require("specialist" in signatures["radioactive"], "radioactive flow lacks specialist decision")
    require("Class 7" in next(node for node in derived["radioactive"] if node["id"] == "specialist")["label"], "radioactive flow lacks Class 7 decision")
    require("inland pre-carriage" in next(node for node in derived["landlocked"] if node["id"] == "route")["label"].lower(), "landlocked flow lacks inland pre-carriage")
    require(next(node for node in derived["complete_cost"] if node["id"] == "cost")["label"] == "Review landed-cost result", "completed cost flow still asks for inputs")
    require("clarify" in signatures["incomplete"], "incomplete shipment lacks clarification decision")
    require(any(node["kind"] == "document" for node in derived["standard"]), "document-shaped node missing")
    require(sum(node["kind"] == "decision" for node in derived["standard"]) >= 3, "standard flow lacks dynamic decisions")
    print("PASS - dynamic signatures differ across ordinary, landlocked, hazardous, radioactive, cost and incomplete cases")
    print("PASS - process rectangles, decision diamonds, document nodes and arrows use structured payload fields")
    print("PASS - dangerous goods and Class 7 cargo receive specialist decisions")


if __name__ == "__main__":
    main()
