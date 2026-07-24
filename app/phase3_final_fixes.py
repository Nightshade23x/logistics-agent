from __future__ import annotations

import re
from typing import Any


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _clean_num(value: Any) -> int | float | None:
    number = _to_float(value)
    if number is None:
        return None
    if abs(number - round(number)) < 0.000001:
        return int(round(number))
    return round(number, 4)


def _prompt_text(payload: Any, prompt: Any = None) -> str:
    if prompt is not None and str(prompt).strip():
        return str(prompt)

    wanted_keys = {
        "prompt",
        "input_text",
        "request_text",
        "query",
        "message",
        "user_message",
        "original_prompt",
        "raw_prompt",
    }

    seen: set[int] = set()

    def walk(obj: Any) -> str:
        obj_id = id(obj)
        if obj_id in seen:
            return ""
        seen.add(obj_id)

        if isinstance(obj, dict):
            for key, value in obj.items():
                if str(key).lower() in wanted_keys and isinstance(value, str) and value.strip():
                    return value

            for value in obj.values():
                found = walk(value)
                if found:
                    return found

        elif isinstance(obj, list):
            for value in obj:
                found = walk(value)
                if found:
                    return found

        return ""

    return walk(payload)


def _quantity(text: str) -> int:
    raw = str(text or "")

    patterns = [
        r"\bship\s+(\d+)\s+(?:[A-Za-z0-9-]+\s+){0,8}?(?:cartons?|boxes?|pallets?|units?|pieces?|pcs|scooters?|machines?|tables?|generators?|tvs?|televisions?)\b",
        r"\bfind\s+suppliers\s+for\s+(\d+)\s+",
        r"\b(\d+)\s+(?:wooden\s+)?tables?\b",
        r"\b(\d+)\s+(?:industrial\s+)?generators?\b",
        r"\b(\d+)\s+(?:electric\s+)?scooters?\b",
        r"\b(\d+)\s+(?:cartons?|boxes?|pallets?|units?|pieces?|pcs)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass

    return 1


def _weight_kg(text: str) -> float | None:
    raw = str(text or "")
    qty = _quantity(raw)

    each_patterns = [
        r"\beach\b[\s\S]{0,400}?\bweighs?\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
        r"\beach\b[\s\S]{0,400}?\band\s+weighs?\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
        r"\beach\b[\s\S]{0,400}?\bweight\s+is\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
    ]

    for pattern in each_patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            unit_weight = _to_float(match.group(1))
            if unit_weight is not None:
                return unit_weight * qty

    total_patterns = [
        r"\btotal\s+cargo\s+is\s+[0-9]+(?:\.[0-9]+)?\s*cbm\s+and\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
        r"\btotal\s+weight\s+is\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
        r"\bship\s+([0-9]+(?:\.[0-9]+)?)\s*kg\s+of\b",
        r"\bcargo\s+weighs?\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
        r"\bweighing\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
        r"\bweight\s+is\s+([0-9]+(?:\.[0-9]+)?)\s*kg\b",
    ]

    for pattern in total_patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            return _to_float(match.group(1))

    return None


def _total_cbm(text: str) -> float | None:
    raw = str(text or "")

    patterns = [
        r"\btotal\s+cargo\s+is\s+([0-9]+(?:\.[0-9]+)?)\s*cbm\b",
        r"\bship\s+([0-9]+(?:\.[0-9]+)?)\s*cbm\s+of\b",
        r"\bcargo\s+volume\s+is\s+([0-9]+(?:\.[0-9]+)?)\s*cbm\b",
        r"\b([0-9]+(?:\.[0-9]+)?)\s*cbm\s+of\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            return _to_float(match.group(1))

    return None


def _has_item_dimensions(text: str) -> bool:
    raw = str(text or "")
    pattern = r"(?:each\s+[\s\S]{0,140}?\s+is|dimensions\s+are)\s+[0-9.]+\s*(?:cm|m|mm|in|ft)?\s*x\s*[0-9.]+\s*(?:cm|m|mm|in|ft)?\s*x\s*[0-9.]+"
    return bool(re.search(pattern, raw, flags=re.IGNORECASE))


def _metrics(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("logistics_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
        payload["logistics_metrics"] = metrics
    return metrics


def _set_weight(payload: dict[str, Any], text: str) -> None:
    weight = _weight_kg(text)
    if weight is None:
        return

    value = _clean_num(weight)
    metrics = _metrics(payload)
    metrics["total_weight_kg"] = value

    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict):
        container = visualizer.get("container")
        if isinstance(container, dict):
            container["total_weight_kg"] = value

        cargo_mix = visualizer.get("cargo_mix")
        if isinstance(cargo_mix, list) and len(cargo_mix) == 1 and isinstance(cargo_mix[0], dict):
            item = cargo_mix[0]
            qty = _quantity(text)
            item["quantity"] = qty
            item["total_weight_kg"] = value
            if qty:
                item["unit_weight_kg"] = _clean_num(float(weight) / float(qty))

            lower = text.lower()
            tags = item.get("category_tags")
            if not isinstance(tags, list):
                tags = []
                item["category_tags"] = tags

            if "hazardous" in lower and "hazardous" not in tags:
                tags.append("hazardous")

            if ("lithium" in lower or "batter" in lower) and "lithium_battery" not in tags:
                tags.append("lithium_battery")

            if "non-stackable" in lower or "non stackable" in lower:
                item["stackable"] = False
                if "non_stackable" not in tags:
                    tags.append("non_stackable")

    for key in ["handoff_payload", "logistics_quality_review"]:
        section = payload.get(key)
        if isinstance(section, dict):
            section["total_weight_kg"] = value


def _fix_aggregate_cbm_container(payload: dict[str, Any], text: str) -> None:
    cbm = _total_cbm(text)
    if cbm is None:
        return

    if _has_item_dimensions(text):
        return

    metrics = _metrics(payload)
    parsed_weight = _weight_kg(text)

    if parsed_weight is not None:
        metrics["total_weight_kg"] = _clean_num(parsed_weight)

    current_weight = _to_float(metrics.get("total_weight_kg"))

    selected = "20ft Standard Container"
    load_type = "fcl_preferred"
    capacity = 33.2
    safe_capacity = 28.22
    max_payload = 28200.0

    if cbm > safe_capacity:
        selected = "40ft Standard Container"
        capacity = 67.7
        safe_capacity = 57.55
        max_payload = 26700.0

    lower = text.lower()
    hazard_tokens = ["hazardous", "lithium", "battery", "batteries", "flammable"]

    if cbm < 10 and not any(token in lower for token in hazard_tokens):
        load_type = "lcl_suitable"

    fit_status = "fits_selected_container"
    if current_weight is not None and current_weight > max_payload:
        fit_status = "payload_limit_review_required"

    metrics["total_cbm"] = _clean_num(cbm)
    metrics["recommended_container"] = selected
    metrics["recommended_load_type"] = load_type

    visualizer = payload.get("logistics_visualizer")
    if not isinstance(visualizer, dict):
        visualizer = {}
        payload["logistics_visualizer"] = visualizer

    visualizer["status"] = "available"

    container = visualizer.get("container")
    if not isinstance(container, dict):
        container = {}
        visualizer["container"] = container

    container.update(
        {
            "selected_container": selected,
            "recommended_load_type": load_type,
            "total_cbm": _clean_num(cbm),
            "total_weight_kg": _clean_num(current_weight),
            "capacity_cbm": capacity,
            "safe_capacity_cbm": safe_capacity,
            "max_payload_kg": max_payload,
            "utilization_percent": round((float(cbm) / float(capacity)) * 100, 2),
        }
    )

    fit = visualizer.get("fit_check")
    if not isinstance(fit, dict):
        fit = {}
        visualizer["fit_check"] = fit

    fit.update(
        {
            "status": fit_status,
            "selected_container_checked": selected,
            "warnings": ["Aggregate CBM was provided; confirm item-level packed dimensions before final loading."],
            "recommendations": ["Use aggregate CBM for first-pass planning and verify item-level dimensions before booking."],
        }
    )


def _fix_missing_only_units(payload: dict[str, Any], text: str) -> None:
    lower = text.lower()

    if "only know" not in lower and "what else" not in lower:
        return

    if _total_cbm(text) is not None:
        return

    if _weight_kg(text) is not None:
        return

    if _has_item_dimensions(text):
        return

    metrics = _metrics(payload)
    metrics.update(
        {
            "total_cbm": None,
            "total_weight_kg": None,
            "recommended_container": None,
            "recommended_load_type": None,
            "risk_level": "moderate" if "fragile" in lower else None,
            "risk_score": 4 if "fragile" in lower else None,
            "readiness_status": "needs_more_information",
        }
    )

    payload["status"] = "needs_more_information"
    payload["logistics_visualizer"] = {
        "status": "unavailable",
        "reason": "Cargo dimensions, CBM, and weight were not provided.",
    }


def _fix_hazardous_load_type(payload: dict[str, Any], text: str) -> None:
    lower = text.lower()
    hazard_tokens = ["hazardous", "lithium", "battery", "batteries", "flammable", "non-stackable", "non stackable"]

    if not any(token in lower for token in hazard_tokens):
        return

    metrics = _metrics(payload)
    if metrics.get("total_cbm") is not None:
        metrics["recommended_load_type"] = "fcl_preferred"

    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict):
        container = visualizer.get("container")
        if isinstance(container, dict) and container.get("total_cbm") is not None:
            container["recommended_load_type"] = "fcl_preferred"


def _fix_trade_plan_agents(payload: dict[str, Any], text: str) -> None:
    if "logistics" not in text.lower():
        return

    metrics = payload.get("logistics_metrics")
    if not isinstance(metrics, dict):
        return

    if metrics.get("total_cbm") is None and metrics.get("total_weight_kg") is None:
        return

    agents = payload.get("agents_called")
    if not isinstance(agents, list):
        agents = []
        payload["agents_called"] = agents

    if "logistics_agent" not in agents:
        agents.insert(0, "logistics_agent")


def apply_phase3_final_fixes(payload: Any, prompt: Any = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = _prompt_text(payload, prompt)

    _set_weight(payload, text)
    _fix_aggregate_cbm_container(payload, text)
    _fix_missing_only_units(payload, text)
    _fix_hazardous_load_type(payload, text)
    _fix_trade_plan_agents(payload, text)

    return payload
