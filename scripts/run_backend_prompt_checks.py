# Prompt checker UTF-8/BOM safety v14
from pathlib import Path
import json
import sys
import traceback
import os
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backend_service import process_text_request

INPUT_PATH = ROOT / "demo_inputs" / "backend_prompts.txt"
OUT_DIR = ROOT / "demo_outputs" / "backend_prompt_checks"
OUT_DIR.mkdir(parents=True, exist_ok=True)

raw = INPUT_PATH.read_text(encoding="utf-8")
prompts = [part.strip().lstrip('\ufeff') for part in raw.split("---") if part.strip().lstrip('\ufeff')]

summary = []

def get_visualizer_status(payload):
    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict):
        return visualizer.get("status")
    return None

def get_fit_status(payload):
    visualizer = payload.get("logistics_visualizer")
    if not isinstance(visualizer, dict):
        return None
    fit = visualizer.get("fit_check")
    if isinstance(fit, dict):
        return fit.get("status")
    return None

def get_doc_item_count(payload):
    doc = payload.get("document_requirements_advice")
    if isinstance(doc, dict):
        return doc.get("item_count")
    return None

def get_landed_cost(payload):
    landed = payload.get("landed_cost_advice")
    if isinstance(landed, dict):
        return landed.get("estimated_landed_cost_usd")
    return None

def leak_flags(payload):
    dumped = json.dumps(payload, ensure_ascii=False, default=str).lower()
    checks = {
        "ceramic tiles exported": "ceramic tiles exported" in dumped,
        "may not physically fit": "may not physically fit" in dumped,
        "switching to 40ft": "switching to 40ft" in dumped,
        "germany the cargo": "germany the cargo" in dumped,
        "no shipment items were found": "no shipment items were found" in dumped,
        "no shipment items were available": "no shipment items were available" in dumped,
    }
    return [key for key, present in checks.items() if present]

for idx, prompt in enumerate(prompts, start=1):
    name = f"q{idx}"
    out_path = OUT_DIR / f"{name}.json"

    try:
        payload = process_text_request(prompt)
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        row = {
            "name": name,
            "prompt": prompt,
            "status": payload.get("status"),
            "intent": payload.get("detected_intent"),
            "agents": payload.get("agents_called"),
            "metrics": payload.get("logistics_metrics"),
            "visualizer": get_visualizer_status(payload),
            "fit": get_fit_status(payload),
            "doc_item_count": get_doc_item_count(payload),
            "landed_cost": get_landed_cost(payload),
            "leaks": leak_flags(payload),
            "json_path": str(out_path),
        }

    except Exception as exc:
        row = {
            "name": name,
            "prompt": prompt,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "json_path": str(out_path),
        }

    summary.append(row)

summary_path = OUT_DIR / "SUMMARY.json"
summary_txt_path = OUT_DIR / "SUMMARY.txt"

summary_path.write_text(
    json.dumps(summary, indent=2, ensure_ascii=False, default=str),
    encoding="utf-8",
)

lines = []
lines.append("=" * 90)
lines.append("BACKEND PROMPT CHECK SUMMARY")
lines.append("=" * 90)

for row in summary:
    lines.append("")
    lines.append(row["name"].upper())
    lines.append("-" * 90)
    lines.append("prompt: " + row.get("prompt", ""))

    if "error" in row:
        lines.append("ERROR: " + row["error"])
        continue

    lines.append("status: " + str(row.get("status")))
    lines.append("intent: " + str(row.get("intent")))
    lines.append("agents: " + str(row.get("agents")))
    lines.append("metrics: " + str(row.get("metrics")))
    lines.append("visualizer: " + str(row.get("visualizer")))
    lines.append("fit: " + str(row.get("fit")))
    lines.append("doc_item_count: " + str(row.get("doc_item_count")))
    lines.append("landed_cost: " + str(row.get("landed_cost")))
    lines.append("leaks: " + str(row.get("leaks")))
    lines.append("json: " + str(row.get("json_path")))

summary_text = "\n".join(lines)
summary_txt_path.write_text(summary_text, encoding="utf-8")

print(summary_text)
print("")
print("Saved summary:", summary_txt_path)
print("Saved JSON summary:", summary_path)
