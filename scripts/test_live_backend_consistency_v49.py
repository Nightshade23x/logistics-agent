from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from app.backend_service import process_text_request

def need(ok, message):
    if not ok: raise AssertionError(message)
def call(prompt):
    try: result = process_text_request(prompt)
    except TypeError: result = process_text_request({"text": prompt})
    need(isinstance(result, dict), type(result)); return result
def metric(payload, key):
    for loc in (payload.get("logistics_metrics"), payload.get("handoff_payload")):
        if isinstance(loc, dict) and isinstance(loc.get(key), (int,float)): return float(loc[key])
def close(a,b): return a is not None and abs(a-b) <= 0.02
def strings(node):
    out=[]
    if isinstance(node, dict):
        for v in node.values(): out += strings(v)
    elif isinstance(node, list):
        for v in node: out += strings(v)
    elif isinstance(node, str): out.append(node)
    return out
def agents(p): return set(map(str,p.get("agents_called",[]))) if isinstance(p.get("agents_called"),list) else set()

def main():
    p=call("Ship 4 crates of ceramic tiles from India to Germany under CIF terms. Each crate measures 1 m x 1 m x 1 m and weighs 200 kg. The tiles are fragile and stackable.")
    need(close(metric(p,"total_cbm"),4),p); need(close(metric(p,"total_weight_kg"),800),p)
    text='\n'.join(strings(p)).lower()
    need("missing dimensions" not in text and "length, width, and height are required" not in text,text)
    need("product 'of ceramic tiles under terms'" not in text,text)
    print("PASS - known dimensions and weight do not reappear as missing")

    p=call("Arrange sea freight for 50 electric scooters from India to Germany under CIF terms. Each scooter is packed in a crate measuring 1.4 m x 0.8 m x 1.35 m and weighs 120 kg. The scooters contain lithium-ion batteries. The battery UN number, watt-hour rating and dangerous-goods documents are not yet confirmed.")
    need(p.get("detected_intent")=="logistics",p); need(close(metric(p,"total_cbm"),75.6),p); need(close(metric(p,"total_weight_kg"),6000),p)
    a=agents(p); need("logistics_agent" in a and "shopping_agent" not in a,a); need("compliance_agent" in a and "document_ai_agent" in a,a)
    lithium_text='\n'.join(strings(p)).lower()
    stale_phrases = (
        "final packed cbm or packed dimensions",
        "package dimensions or total packed volume",
        "cargo volume or dimensions were not provided",
        "missing cargo size information",
        "total volume: not confirmed",
        "trader agent failed: 'gemini_api_key'",
    )
    need(not any(phrase in lithium_text for phrase in stale_phrases), lithium_text)
    need("75.6 cbm" in lithium_text, lithium_text)
    need("6,000 kg" in lithium_text or "6000 kg" in lithium_text, lithium_text)
    summaries=p.get("agent_summaries",[])
    summary_agents={x.get("agent_name") for x in summaries if isinstance(x,dict)}
    need("compliance_agent" in summary_agents and "document_ai_agent" in summary_agents,summaries)
    visual=p.get("logistics_visualizer",{})
    need(isinstance(visual,dict) and visual.get("status") in {"review_required","available"},visual)
    need(close((visual.get("container") or {}).get("total_cbm"),75.6),visual)
    print("PASS - lithium shipment keeps authoritative totals, specialist routing and consistent visible output")

    p=call("I need to ship a radioactive medical source from South Africa to Kenya. The isotope, activity level, UN number, packed dimensions and packed weight are not yet confirmed. Tell me what information and documents are required.")
    a=agents(p); need(p.get("detected_intent")=="logistics",p); need("shopping_agent" not in a,a); need("compliance_agent" in a and "document_ai_agent" in a,a)
    print("PASS - radioactive shipment remains logistics in final payload")

    p=call("Ship 4 crates of ceramic tiles from India to Germany. Packed dimensions are unknown.")
    text='\n'.join(strings(p)).lower(); need("dimension" in text or "length" in text or "packed size" in text,p)
    print("PASS - truly missing dimensions still produce clarification")

    p=call("Ship 10 crates from India to Germany. Each crate weighs 100 kg, but the total shipment weight is 150 kg. Each crate is 1 m x 1 m x 1 m.")
    need(close(metric(p,"total_weight_kg"),150),p)
    validation=p.get("input_validation_v44",{})
    authority=validation.get("authoritative_facts",{}) if isinstance(validation,dict) else {}
    need(close(authority.get("explicit_total_weight_kg"),150),authority)
    need(close(authority.get("derived_total_weight_kg"),1000),authority)
    need(close(authority.get("total_weight_kg"),150),authority)
    metadata=p.get("request_metadata",{})
    original=str(metadata.get("original_input_source", "")) if isinstance(metadata,dict) else ""
    need("150 kg" in original and "1,000 kg" not in original,metadata)
    need("confirm whether the explicit total shipment weight" in '\n'.join(strings(p)).lower(),p)
    print("PASS - explicit conflicting shipment total remains authoritative while derived weight is retained")

    p=call("Ship 10 crates of ceramic tiles from India to Germany, each weighing 100 kg. Correction: the quantity is 12, not 10.")
    need(metric(p,"total_cbm") is None,p)
    need(close(metric(p,"total_weight_kg"),1200),p)
    validation=p.get("input_validation_v44",{})
    authority=validation.get("authoritative_facts",{}) if isinstance(validation,dict) else {}
    need(close(authority.get("quantity"),12),authority)
    need(close(authority.get("derived_total_weight_kg"),1200),authority)
    metadata=p.get("request_metadata",{})
    consistency=metadata.get("live_response_consistency_v49",{}) if isinstance(metadata,dict) else {}
    need(consistency.get("correction_quantity_preserved") is True,consistency)
    need(close(consistency.get("authoritative_quantity_used"),12),consistency)
    need(consistency.get("physical_override_blocked") is True,consistency)
    need("correction_without_dimensions" in consistency.get("physical_override_reasons",[]),consistency)
    print("PASS - corrected quantity remains authoritative without bypassing the CBM guard")

    invalid_prompts = [
        "Ship -5 crates of machinery from India to Germany. Each crate weighs -20 kg and measures -1 m x 1 m x 1 m.",
        "Ship 0 pallets of ceramic tiles from India to Germany. Each pallet weighs 500 kg and measures 1.2 m x 1 m x 1.4 m.",
    ]
    for invalid_prompt in invalid_prompts:
        invalid=call(invalid_prompt)
        need(metric(invalid,"total_cbm") is None,invalid)
        need(metric(invalid,"total_weight_kg") is None,invalid)
        validation=invalid.get("input_validation_v44",{})
        need(bool(validation.get("errors")) if isinstance(validation,dict) else False,invalid)
        metadata=invalid.get("request_metadata",{})
        consistency=metadata.get("live_response_consistency_v49",{}) if isinstance(metadata,dict) else {}
        need(consistency.get("physical_override_blocked") is True,consistency)
    print("PASS - negative and zero physical inputs remain blocked by V44 authority")

    unknown=call("Source 500 ceramic tiles in India and ship them to Germany. Dimensions, weight, freight, duty, and tax are unknown.")
    need(metric(unknown,"total_cbm") is None,unknown)
    need(metric(unknown,"total_weight_kg") is None,unknown)
    print("PASS - explicit unknown physical facts cannot be replaced by V49 defaults")

    # Landed-cost extraction is an API-level workflow. A direct call to
    # backend_service.process_text_request does not reproduce the API request
    # enrichment used by the established V36 regression. The real API test
    # scripts/test_completed_landed_cost_answer_v36.py runs immediately after
    # this focused test and is the authoritative check for the $21,025.34 flow.
    print("PASS - landed-cost compatibility is delegated to the authoritative V36 API regression")

    p=call("I need 50 TVs from India to USA under FOB Mumbai terms. Compare suppliers and prices.")
    need(p.get("detected_intent")=="shopping" and "shopping_agent" in agents(p),p)
    print("PASS - genuine procurement remains shopping")
    print("All V49 live-backend consistency tests passed.")
if __name__=='__main__': main()
