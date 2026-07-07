"""
Client adapter for Avishi's Trade Orchestrator.

The orchestrator is treated as one specialist partner service:
Trade Review / Compliance / Finance / Risk.

Transport:
    REST / FastAPI

Expected endpoint:
    POST {TRADE_ORCHESTRATOR_BASE_URL}/orchestrate

Expected input:
    {"query": "free-text shipment description"}

Output:
    Raw orchestrator response is normalized into Samar's partner-review
    response shape so the rest of the backend can keep using its existing
    final verdict, booking readiness, executive summary, and frontend payload
    builders.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Optional


ORCHESTRATOR_ENV_VAR = "TRADE_ORCHESTRATOR_BASE_URL"


STATUS_MAP = {
    "clear": "ready_for_review",
    "review_required": "review_required",
    "blocked": "blocked",
    "error": "error",
}


def map_orchestrator_status(status: Optional[str]) -> str:
    """Map Avishi's orchestrator verdict status into Samar's status vocabulary."""
    if not status:
        return "review_required"
    return STATUS_MAP.get(str(status).strip().lower(), "review_required")


def _recursive_find_first(data: Any, keys: Iterable[str]) -> Any:
    wanted = {k.lower() for k in keys}

    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in wanted and value not in (None, "", [], {}):
                return value

        for value in data.values():
            found = _recursive_find_first(value, wanted)
            if found not in (None, "", [], {}):
                return found

    elif isinstance(data, list):
        for item in data:
            found = _recursive_find_first(item, wanted)
            if found not in (None, "", [], {}):
                return found

    return None


def _recursive_find_items(data: Any) -> List[Dict[str, Any]]:
    item_keys = {
        "items",
        "selected_items",
        "line_items",
        "cargo_items",
        "products",
        "shipment_items",
    }

    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in item_keys and isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        for value in data.values():
            found = _recursive_find_items(value)
            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = _recursive_find_items(item)
            if found:
                return found

    return []


def _item_name(item: Dict[str, Any]) -> str:
    return str(
        item.get("product_name")
        or item.get("product_description")
        or item.get("item_name")
        or item.get("name")
        or item.get("description")
        or "item"
    )


def _item_quantity(item: Dict[str, Any]) -> Any:
    return (
        item.get("quantity")
        or item.get("qty")
        or item.get("units")
        or item.get("count")
        or ""
    )


def _summarize_items(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "the shipment"

    parts: List[str] = []
    for item in items[:8]:
        quantity = _item_quantity(item)
        name = _item_name(item)
        if quantity not in (None, ""):
            parts.append(f"{quantity} {name}")
        else:
            parts.append(name)

    if len(items) > 8:
        parts.append(f"{len(items) - 8} more item types")

    if len(parts) == 1:
        return parts[0]

    return ", ".join(parts[:-1]) + " and " + parts[-1]


def build_trade_orchestrator_query(partner_payload: Dict[str, Any]) -> str:
    """
    Convert Samar's structured partner-review/logistics payload into the
    free-text query currently expected by Avishi's orchestrator.
    """
    origin = _recursive_find_first(
        partner_payload,
        [
            "origin_country",
            "country_from",
            "export_country",
            "supplier_country",
            "source_country",
        ],
    )
    destination = _recursive_find_first(
        partner_payload,
        [
            "destination_country",
            "country_to",
            "import_country",
            "target_market",
            "buyer_country",
        ],
    )
    incoterm = _recursive_find_first(
        partner_payload,
        ["incoterm", "trade_term", "shipping_terms", "terms"],
    )
    value = _recursive_find_first(
        partner_payload,
        [
            "procurement_value_usd",
            "declared_value_usd",
            "cargo_value",
            "cargo_value_usd",
            "estimated_total_usd",
            "total_value_usd",
        ],
    )
    weight = _recursive_find_first(
        partner_payload,
        ["total_weight_kg", "weight_kg", "gross_weight_kg"],
    )
    cbm = _recursive_find_first(
        partner_payload,
        ["total_cbm", "volume_m3", "total_volume_m3", "cbm"],
    )
    currency = (
        _recursive_find_first(partner_payload, ["currency"])
        or "USD"
    )

    items = _recursive_find_items(partner_payload)
    item_summary = _summarize_items(items)

    sentence_parts = [f"Ship {item_summary}"]

    if origin and destination:
        sentence_parts.append(f"from {origin} to {destination}")
    elif origin:
        sentence_parts.append(f"from {origin}")
    elif destination:
        sentence_parts.append(f"to {destination}")

    details = []
    if incoterm:
        details.append(f"Incoterm {incoterm}")
    if value:
        details.append(f"Estimated cargo/procurement value {value} {currency}")
    if weight:
        details.append(f"Total weight {weight} kg")
    if cbm:
        details.append(f"Total volume {cbm} m3")

    query = " ".join(sentence_parts).strip()
    if details:
        query += ". " + ". ".join(details) + "."

    return query


def _post_json(url: str, payload: Dict[str, Any], timeout_seconds: int) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_body = response.read().decode("utf-8")
        return json.loads(response_body)


def call_trade_orchestrator(
    partner_payload: Dict[str, Any],
    *,
    base_url: Optional[str] = None,
    timeout_seconds: int = 30,
    http_post: Optional[Callable[[str, Dict[str, Any], int], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Call Avishi's orchestrator and return its raw response.

    http_post is injectable for tests so we can validate mapping without
    needing the live server running.
    """
    resolved_base_url = (base_url or os.getenv(ORCHESTRATOR_ENV_VAR, "")).strip()

    if not resolved_base_url:
        raise RuntimeError(f"{ORCHESTRATOR_ENV_VAR} is not configured.")

    endpoint = resolved_base_url.rstrip("/") + "/orchestrate"
    query = build_trade_orchestrator_query(partner_payload)
    request_payload = {"query": query}

    poster = http_post or _post_json
    return poster(endpoint, request_payload, timeout_seconds)


def _collect_missing_information(raw: Dict[str, Any]) -> List[str]:
    missing: List[str] = []

    for report_key in ["compliance_report", "trader_report", "risk_report"]:
        report = raw.get(report_key)
        if isinstance(report, dict):
            values = report.get("missing_information")
            if isinstance(values, list):
                missing.extend(str(item) for item in values)

    verdict = raw.get("verdict")
    if isinstance(verdict, dict):
        for key in ["warnings", "blockers", "next_steps"]:
            values = verdict.get(key)
            if isinstance(values, list):
                missing.extend(str(item) for item in values)

    seen = set()
    deduped = []
    for item in missing:
        if item not in seen:
            deduped.append(item)
            seen.add(item)

    return deduped


def normalize_trade_orchestrator_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Avishi's orchestrator output into Samar's partner-review style.
    """
    verdict = raw.get("verdict") if isinstance(raw.get("verdict"), dict) else {}
    original_status = verdict.get("status")
    mapped_status = map_orchestrator_status(original_status)

    headline = (
        verdict.get("headline")
        or raw.get("synthesis")
        or "Trade orchestrator review completed."
    )

    finance_report = raw.get("finance_report") if isinstance(raw.get("finance_report"), dict) else {}
    trader_report = raw.get("trader_report") if isinstance(raw.get("trader_report"), dict) else {}
    risk_report = raw.get("risk_report") if isinstance(raw.get("risk_report"), dict) else {}

    trader_handoff = trader_report.get("handoff_payload") if isinstance(trader_report.get("handoff_payload"), dict) else {}
    risk_handoff = risk_report.get("handoff_payload") if isinstance(risk_report.get("handoff_payload"), dict) else {}

    return {
        "agent_name": "partner_trade_orchestrator",
        "status": mapped_status,
        "summary": headline,
        "plan": [
            "Called Avishi's Trade Orchestrator as one specialist partner service.",
            "Received combined risk, compliance, trader, and finance review.",
            "Mapped orchestrator verdict into Samar backend status vocabulary.",
        ],
        "report": {
            "request_id": raw.get("request_id"),
            "parsed_shipment": raw.get("parsed_shipment", {}),
            "verdict": verdict,
            "synthesis": raw.get("synthesis"),
            "risk_report": raw.get("risk_report", {}),
            "compliance_report": raw.get("compliance_report", {}),
            "trader_report": raw.get("trader_report", {}),
            "finance_report": raw.get("finance_report", {}),
            "agent_errors": raw.get("agent_errors", {}),
        },
        "input_resolution": raw.get("parsed_shipment", {}),
        "missing_information": _collect_missing_information(raw),
        "handoff_payload": {
            "partner_service": "trade_orchestrator",
            "orchestrator_request_id": raw.get("request_id"),
            "orchestrator_status": original_status,
            "mapped_status": mapped_status,
            "verdict": verdict,
            "synthesis": raw.get("synthesis"),
            "landed_cost": finance_report.get("landed_cost"),
            "total_cost": finance_report.get("total_cost"),
            "freight_cost": finance_report.get("freight_cost"),
            "insurance_cost": finance_report.get("insurance_cost"),
            "import_duty": finance_report.get("import_duty"),
            "taxes": finance_report.get("taxes"),
            "currency": finance_report.get("currency"),
            "hs_code": trader_handoff.get("hs_code"),
            "duty_rate_percent": trader_handoff.get("duty_rate_percent"),
            "fta_exists": trader_handoff.get("fta_exists"),
            "risk_tier": risk_handoff.get("risk_tier"),
            "cpi_score": risk_handoff.get("cpi_score"),
            "sanctions_status": risk_handoff.get("sanctions_status"),
            "agent_errors": raw.get("agent_errors", {}),
        },
        "handoff_requests": [],
    }


def run_trade_orchestrator_review(
    partner_payload: Dict[str, Any],
    *,
    base_url: Optional[str] = None,
    timeout_seconds: int = 30,
    http_post: Optional[Callable[[str, Dict[str, Any], int], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    High-level adapter function used by partner_review_service.py.
    """
    resolved_base_url = (base_url or os.getenv(ORCHESTRATOR_ENV_VAR, "")).strip()

    if not resolved_base_url:
        return {
            "agent_name": "partner_trade_orchestrator",
            "status": "partner_review_not_configured",
            "summary": f"{ORCHESTRATOR_ENV_VAR} is not configured, so the live trade orchestrator was not called.",
            "plan": [],
            "report": {},
            "input_resolution": {},
            "missing_information": [f"Set {ORCHESTRATOR_ENV_VAR}=http://localhost:8010 to call Avishi's orchestrator."],
            "handoff_payload": {
                "partner_service": "trade_orchestrator",
                "configured": False,
            },
            "handoff_requests": [],
        }

    try:
        raw = call_trade_orchestrator(
            partner_payload,
            base_url=resolved_base_url,
            timeout_seconds=timeout_seconds,
            http_post=http_post,
        )
        normalized = normalize_trade_orchestrator_response(raw)
        normalized["handoff_payload"]["configured"] = True
        normalized["handoff_payload"]["base_url"] = resolved_base_url
        return normalized

    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError, OSError) as exc:
        return {
            "agent_name": "partner_trade_orchestrator",
            "status": "error",
            "summary": f"Trade orchestrator call failed: {exc}",
            "plan": ["Attempted to call Avishi's Trade Orchestrator."],
            "report": {"error": str(exc)},
            "input_resolution": {},
            "missing_information": ["Check that Avishi's orchestrator is running and TRADE_ORCHESTRATOR_BASE_URL is correct."],
            "handoff_payload": {
                "partner_service": "trade_orchestrator",
                "configured": True,
                "base_url": resolved_base_url,
                "error": str(exc),
            },
            "handoff_requests": [],
        }
