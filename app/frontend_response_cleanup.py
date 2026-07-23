from __future__ import annotations

import re
from typing import Any


_BAD_ROUTE_PATTERNS = [
    (re.compile(r"\bUSA\s+Glass bottles are fragile Use FOB\b", re.IGNORECASE), "USA"),
    (re.compile(r"\bUSA\s+Give HS code duty FTA\b", re.IGNORECASE), "USA"),
    (re.compile(r"\bUSA\?\s+Tell me compliance risk logistics\b", re.IGNORECASE), "USA"),
    (
        re.compile(
            r"\bUSA(?:\?|\.|,)?\s+(?:Glass|Give|Tell|Use|The|They|compliance|risk|logistics|HS|code|duty|FTA)[^.,;]*",
            re.IGNORECASE,
        ),
        "USA",
    ),
    (
        re.compile(
            r"\bUnited States\s+(?:using|Use|They|The|Give|Tell)[^.,;]*",
            re.IGNORECASE,
        ),
        "USA",
    ),
]


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _extract_text(payload: Any, fallback: str | None = None) -> str:
    if fallback:
        return str(fallback)

    if isinstance(payload, dict):
        request_metadata = payload.get("request_metadata")
        if isinstance(request_metadata, dict) and request_metadata.get("input_source"):
            return str(request_metadata.get("input_source"))

        for key in ["input_source", "user_text", "request_text", "original_text", "prompt"]:
            if payload.get(key):
                return str(payload.get(key))

    return ""


def _clean_country(value: str | None) -> str | None:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z. ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    aliases = {
        "usa": "USA",
        "us": "USA",
        "u.s.": "USA",
        "u.s.a.": "USA",
        "united states": "USA",
        "united states of america": "USA",
        "india": "India",
        "china": "China",
        "turkey": "Turkey",
        "turkiye": "Turkey",
        "uk": "UK",
        "united kingdom": "UK",
        "uae": "UAE",
        "iran": "Iran",
        "germany": "Germany",
        "zambia": "Zambia",
        "finland": "Finland",
    }

    for alias in sorted(aliases, key=len, reverse=True):
        if text == alias or text.startswith(alias + " "):
            return aliases[alias]

    return None


def _extract_route(text: str) -> dict[str, str | None]:
    route = {"country_from": None, "country_to": None}

    match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?=\.|,|;|\?|\buse\b|\busing\b|\bwith\b|\bunder\b|\btell\b|\bgive\b|\bglass\b|\bthe\b|\bthey\b|$)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        route["country_from"] = _clean_country(match.group(1))
        route["country_to"] = _clean_country(match.group(2))

    if not route["country_to"]:
        match = re.search(
            r"\bto\s+(USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|India|China|Turkey|Turkiye|UK|United Kingdom|UAE|Iran|Germany|Zambia|Finland)\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            route["country_to"] = _clean_country(match.group(1))

    if not route["country_from"]:
        match = re.search(
            r"\bfrom\s+(USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|India|China|Turkey|Turkiye|UK|United Kingdom|UAE|Iran|Germany|Zambia|Finland)\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            route["country_from"] = _clean_country(match.group(1))

    return route


def _extract_trade_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    incoterms = "EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP"

    for pattern in [
        rf"\buse\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\busing\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\bwith\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\bunder\s+(?:the\s+)?(?:incoterm\s+)?({incoterms})\b",
        rf"\bincoterm\s*(?:is|=|:)?\s*({incoterms})\b",
    ]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            fields["incoterm"] = match.group(1).upper()
            fields["trade_term"] = match.group(1).upper()
            break

    cost_patterns = {
        "freight_quote_usd": r"\bfreight\s+quote\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
        "insurance_premium_usd": r"\binsurance\s*(?:premium|cost|quote)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
        "duty_rate_percent": r"\bduty\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
        "import_tax_rate_percent": r"\bimport\s+tax\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
    }

    for key, pattern in cost_patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _as_float(match.group(1))
            if value is not None:
                fields[key] = value

    return fields


def _extract_totals(text: str) -> dict[str, float]:
    totals: dict[str, float] = {}

    cbm_match = re.search(
        r"\b(?:total\s+)?(?:cargo|shipment|load)\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:cbm|m3|cubic\s+meters?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if cbm_match:
        value = _as_float(cbm_match.group(1))
        if value is not None:
            totals["total_cbm"] = value

    kg_match = re.search(
        r"\b(?:total\s+)?(?:cargo|shipment|load).*?([0-9][0-9,.]*)\s*(?:kg|kgs|kilograms?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if kg_match:
        value = _as_float(kg_match.group(1))
        if value is not None:
            totals["total_weight_kg"] = value

    return totals


def _clean_string(value: str, destination: str | None) -> str:
    result = value

    for pattern, replacement in _BAD_ROUTE_PATTERNS:
        result = pattern.sub(destination or replacement, result)

    return result


def _filter_missing_list(values: list[Any], trade_fields: dict[str, Any], destination: str | None) -> list[Any]:
    known = set(trade_fields.keys()) | {"trade_term"}

    cleaned: list[Any] = []

    for value in values:
        text = str(value).strip()
        lower = text.lower()

        if destination and lower == "destination country":
            continue

        if trade_fields.get("incoterm") and (
            "which incoterm" in lower
            or "incoterm is missing" in lower
            or "no incoterm" in lower
            or lower == "trade_terms needs more information."
        ):
            continue

        if text in known:
            continue

        if text.startswith("landed cost input: "):
            key = text.replace("landed cost input: ", "", 1)
            if key in known:
                continue

        cleaned.append(value)

    return cleaned


def _apply_totals(payload: dict[str, Any], totals: dict[str, float]) -> None:
    if not totals:
        return

    metrics = payload.setdefault("logistics_metrics", {})
    if isinstance(metrics, dict):
        metrics.update(totals)

    visualizer = payload.get("logistics_visualizer")
    if not isinstance(visualizer, dict):
        return

    container = visualizer.setdefault("container", {})
    if isinstance(container, dict):
        container.update(totals)

    cargo_mix = visualizer.get("cargo_mix")
    if isinstance(cargo_mix, list) and cargo_mix:
        first = cargo_mix[0]
        if isinstance(first, dict):
            quantity = first.get("quantity") or 1
            try:
                quantity = float(quantity)
            except Exception:
                quantity = 1.0

            if "total_cbm" in totals:
                first["total_cbm"] = totals["total_cbm"]
                if quantity:
                    first["unit_cbm"] = round(totals["total_cbm"] / quantity, 6)

            if "total_weight_kg" in totals:
                first["total_weight_kg"] = totals["total_weight_kg"]
                if quantity:
                    first["unit_weight_kg"] = round(totals["total_weight_kg"] / quantity, 6)


def cleanup_frontend_response(payload: Any, original_text: str | None = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = _extract_text(payload, original_text)
    route = _extract_route(text)
    origin = route.get("country_from")
    destination = route.get("country_to")
    trade_fields = _extract_trade_fields(text)
    totals = _extract_totals(text)

    def visit(obj: Any, path: str = "") -> Any:
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                value = obj[key]
                lower_key = str(key).lower()

                if path.endswith("request_metadata") and lower_key == "input_source":
                    continue

                if origin and lower_key in {"origin", "origin_country", "country_from"}:
                    obj[key] = origin
                    continue

                if destination and lower_key in {"destination", "destination_country", "country_to", "target_market"}:
                    obj[key] = destination
                    continue

                if lower_key in {"incoterm", "trade_term"} and trade_fields.get(lower_key):
                    obj[key] = trade_fields[lower_key]
                    continue

                obj[key] = visit(value, f"{path}.{key}" if path else str(key))

            known_inputs = obj.get("known_inputs")
            if isinstance(known_inputs, dict):
                if origin:
                    known_inputs["origin_country"] = origin
                if destination:
                    known_inputs["destination_country"] = destination
                known_inputs.update(trade_fields)

            for list_key in ["missing_cost_inputs", "missing_information", "missing_information_preview", "user_questions"]:
                if isinstance(obj.get(list_key), list):
                    obj[list_key] = _filter_missing_list(obj[list_key], trade_fields, destination)

            return obj

        if isinstance(obj, list):
            filtered = _filter_missing_list(obj, trade_fields, destination)
            return [visit(item, f"{path}[]") for item in filtered]

        if isinstance(obj, str):
            return _clean_string(obj, destination)

        return obj

    payload = visit(payload)

    if trade_fields:
        payload.setdefault("text_cost_inputs", {})
        if isinstance(payload["text_cost_inputs"], dict):
            payload["text_cost_inputs"].update(trade_fields)

    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict) and not visualizer.get("cargo_mix"):
        visualizer["status"] = "unavailable"

    _apply_totals(payload, totals)

    return payload


# Logistics plan visualizer exposure v1.
# Builds top-level logistics_metrics and logistics_visualizer from nested Logistics Agent plan
# when the direct response does not already expose them.
try:
    _cleanup_frontend_response_before_plan_visualizer_v1 = cleanup_frontend_response

    def _plan_viz_num(*values, default=0.0):
        for value in values:
            if value is None or value == "":
                continue
            try:
                return float(value)
            except Exception:
                continue
        return float(default)

    def _get_nested_logistics_response_for_plan_visualizer(payload):
        if not isinstance(payload, dict):
            return None

        specialist_responses = payload.get("specialist_responses")
        if isinstance(specialist_responses, dict):
            logistics = specialist_responses.get("logistics_agent")
            if isinstance(logistics, dict):
                return logistics

        specialist_response = payload.get("specialist_response")
        if isinstance(specialist_response, dict) and specialist_response.get("agent_name") == "logistics_agent":
            return specialist_response

        return None

    def _build_visualizer_from_logistics_plan(payload):
        logistics = _get_nested_logistics_response_for_plan_visualizer(payload)
        if not isinstance(logistics, dict):
            return

        plan = logistics.get("plan")
        if not isinstance(plan, dict):
            return

        summary = plan.get("shipment_summary") if isinstance(plan.get("shipment_summary"), dict) else {}
        recommendation = plan.get("container_recommendation") if isinstance(plan.get("container_recommendation"), dict) else {}
        risk = plan.get("logistics_risk") if isinstance(plan.get("logistics_risk"), dict) else {}
        load_type = plan.get("shipping_load_type") if isinstance(plan.get("shipping_load_type"), dict) else {}
        fit = plan.get("container_fit") if isinstance(plan.get("container_fit"), dict) else {}
        layout = plan.get("container_layout") if isinstance(plan.get("container_layout"), dict) else {}

        logistics_input = payload.get("logistics_input") if isinstance(payload.get("logistics_input"), dict) else {}
        input_items = logistics_input.get("items") if isinstance(logistics_input.get("items"), list) else []

        selected_container = (
            recommendation.get("container_name")
            or payload.get("recommended_container")
            or logistics_input.get("recommended_container")
            or logistics_input.get("requested_container")
        )

        total_cbm = _plan_viz_num(summary.get("total_cbm"), logistics_input.get("total_cbm"), default=0.0)
        total_weight_kg = _plan_viz_num(summary.get("total_weight_kg"), logistics_input.get("total_weight_kg"), default=0.0)

        if not isinstance(payload.get("logistics_metrics"), dict) or not payload.get("logistics_metrics"):
            payload["logistics_metrics"] = {
                "total_cbm": total_cbm,
                "total_weight_kg": total_weight_kg,
                "recommended_container": selected_container,
                "recommended_load_type": load_type.get("recommended_load_type"),
                "risk_level": risk.get("risk_level"),
                "risk_score": risk.get("risk_score"),
                "readiness_status": (
                    (plan.get("readiness_checklist") or {}).get("readiness_status")
                    if isinstance(plan.get("readiness_checklist"), dict)
                    else None
                ),
            }

        item_breakdown = plan.get("item_breakdown") if isinstance(plan.get("item_breakdown"), list) else []
        cargo_mix = []

        for index, item in enumerate(item_breakdown):
            if not isinstance(item, dict):
                continue

            source_item = input_items[index] if index < len(input_items) and isinstance(input_items[index], dict) else {}

            item_name = item.get("name") or item.get("item_name")
            if not item_name or str(item_name).lower() == "unknown item":
                item_name = source_item.get("name") or source_item.get("item_name") or item_name or "cargo"

            quantity = _plan_viz_num(item.get("quantity"), source_item.get("quantity"), default=1.0)
            length = _plan_viz_num(item.get("length_m"), source_item.get("length_m"), default=1.0)
            width = _plan_viz_num(item.get("width_m"), source_item.get("width_m"), default=1.0)
            height = _plan_viz_num(item.get("height_m"), source_item.get("height_m"), default=1.0)

            unit_cbm = _plan_viz_num(item.get("unit_cbm"), source_item.get("unit_cbm"), default=length * width * height)
            item_total_cbm = _plan_viz_num(item.get("total_cbm"), source_item.get("total_cbm"), default=unit_cbm * quantity)

            unit_weight = _plan_viz_num(
                item.get("weight_kg"),
                item.get("unit_weight_kg"),
                source_item.get("weight_kg"),
                source_item.get("unit_weight_kg"),
                default=0.0,
            )

            item_total_weight = _plan_viz_num(
                item.get("total_weight_kg"),
                source_item.get("total_weight_kg"),
                default=unit_weight * quantity,
            )

            if unit_weight <= 0 and item_total_weight > 0 and quantity > 0:
                unit_weight = item_total_weight / quantity

            categories = []
            for key in ["cargo_categories", "category_tags", "categories"]:
                value = item.get(key)
                if isinstance(value, list):
                    categories.extend(str(entry) for entry in value if entry)
                value = source_item.get(key)
                if isinstance(value, list):
                    categories.extend(str(entry) for entry in value if entry)

            cargo_mix.append({
                "item_name": str(item_name),
                "quantity": int(quantity) if float(quantity).is_integer() else quantity,
                "dimensions_m": {
                    "length": length,
                    "width": width,
                    "height": height,
                },
                "unit_cbm": round(unit_cbm, 4),
                "total_cbm": round(item_total_cbm, 4),
                "unit_weight_kg": round(unit_weight, 4),
                "total_weight_kg": round(item_total_weight, 4),
                "stackable": bool(item.get("stackable", source_item.get("stackable", True))),
                "unload_priority": item.get("unload_priority", source_item.get("unload_priority", 3)),
                "category_tags": sorted(set(categories)),
            })

        if not cargo_mix and input_items:
            for source_item in input_items:
                if not isinstance(source_item, dict):
                    continue
                dims = source_item.get("dimensions_m") if isinstance(source_item.get("dimensions_m"), dict) else {}
                cargo_mix.append({
                    "item_name": str(source_item.get("name") or source_item.get("item_name") or "cargo"),
                    "quantity": source_item.get("quantity", 1),
                    "dimensions_m": {
                        "length": _plan_viz_num(source_item.get("length_m"), dims.get("length"), default=1.0),
                        "width": _plan_viz_num(source_item.get("width_m"), dims.get("width"), default=1.0),
                        "height": _plan_viz_num(source_item.get("height_m"), dims.get("height"), default=1.0),
                    },
                    "unit_cbm": _plan_viz_num(source_item.get("unit_cbm"), default=1.0),
                    "total_cbm": _plan_viz_num(source_item.get("total_cbm"), default=1.0),
                    "unit_weight_kg": _plan_viz_num(source_item.get("weight_kg"), source_item.get("unit_weight_kg"), default=0.0),
                    "total_weight_kg": _plan_viz_num(source_item.get("total_weight_kg"), default=0.0),
                    "stackable": bool(source_item.get("stackable", True)),
                    "unload_priority": source_item.get("unload_priority", 3),
                    "category_tags": source_item.get("category_tags") or source_item.get("cargo_categories") or [],
                })

        if not cargo_mix:
            return

        container_options = plan.get("container_options") if isinstance(plan.get("container_options"), list) else []
        normalized_options = []
        for option in container_options:
            if not isinstance(option, dict):
                continue
            normalized_options.append({
                "option_name": option.get("option_name"),
                "container_count": option.get("container_count"),
                "total_capacity_cbm": option.get("total_capacity_cbm"),
                "safe_capacity_cbm": option.get("safe_capacity_cbm") or option.get("total_safe_cbm"),
                "payload_limit_kg": option.get("payload_limit_kg") or option.get("total_payload_kg"),
                "estimated_utilization_percent": option.get("estimated_utilization_percent"),
                "unused_safe_cbm": option.get("unused_safe_cbm"),
                "reason": option.get("reason"),
            })

        zone_layout = layout.get("zones") if isinstance(layout.get("zones"), list) else []
        loading_sequence_raw = plan.get("loading_sequence") if isinstance(plan.get("loading_sequence"), list) else []
        loading_sequence = []

        for index, step in enumerate(loading_sequence_raw, start=1):
            if not isinstance(step, dict):
                continue
            step_name = step.get("item_name")
            if not step_name or str(step_name).lower() == "unknown item":
                step_name = cargo_mix[0].get("item_name") if cargo_mix else step_name

            loading_sequence.append({
                "sequence_number": step.get("sequence_number") or index,
                "item_name": step_name,
                "quantity": step.get("quantity", 1),
                "suggested_zone": step.get("suggested_zone"),
                "category_tags": step.get("category_tags") or step.get("categories") or [],
                "reason": step.get("reason"),
            })

        fit_check = {
            "status": fit.get("fit_status"),
            "selected_container_checked": fit.get("selected_container_checked"),
            "warnings": fit.get("warnings") if isinstance(fit.get("warnings"), list) else [],
            "recommendations": fit.get("recommendations") if isinstance(fit.get("recommendations"), list) else [],
            "item_fit_results": fit.get("item_fit_results") if isinstance(fit.get("item_fit_results"), list) else [],
        }

        if fit_check["item_fit_results"]:
            for index, fit_item in enumerate(fit_check["item_fit_results"]):
                if isinstance(fit_item, dict) and str(fit_item.get("item_name", "")).lower() == "unknown item":
                    if index < len(cargo_mix):
                        fit_item["item_name"] = cargo_mix[index].get("item_name")

        payload["logistics_visualizer"] = {
            "visualizer_type": "container_load_visualizer",
            "status": "available",
            "container": {
                "selected_container": selected_container,
                "recommended_load_type": load_type.get("recommended_load_type"),
                "total_cbm": total_cbm,
                "total_weight_kg": total_weight_kg,
                "total_items": summary.get("total_items"),
                "capacity_cbm": recommendation.get("capacity_cbm"),
                "safe_capacity_cbm": recommendation.get("safe_cbm_limit"),
                "max_payload_kg": recommendation.get("max_payload_kg"),
                "utilization_percent": recommendation.get("estimated_utilization_percent"),
                "risk_level": risk.get("risk_level"),
                "risk_score": risk.get("risk_score"),
            },
            "cargo_mix": cargo_mix,
            "container_options": normalized_options,
            "zone_layout": zone_layout,
            "loading_sequence": loading_sequence,
            "fit_check": fit_check,
            "layout_notes": layout.get("layout_notes") if isinstance(layout.get("layout_notes"), list) else [],
            "frontend_hints": {
                "primary_view": "container_utilization",
                "secondary_view": "zone_layout",
                "show_cargo_tags": True,
                "show_fit_warnings": True,
                "show_loading_sequence": True,
            },
        }

    def cleanup_frontend_response(payload, original_text=None):
        cleaned = _cleanup_frontend_response_before_plan_visualizer_v1(payload, original_text)
        try:
            _build_visualizer_from_logistics_plan(cleaned)
        except Exception:
            pass
        return cleaned

except Exception:
    pass


# Safe top-level logistics handoff exposure v2.
try:
    _cleanup_frontend_response_before_safe_handoff_v2 = cleanup_frontend_response

    def _safe_handoff_v2_get_logistics(payload):
        if not isinstance(payload, dict):
            return None

        specialist_responses = payload.get("specialist_responses")
        if isinstance(specialist_responses, dict):
            logistics = specialist_responses.get("logistics_agent")
            if isinstance(logistics, dict):
                return logistics

        specialist_response = payload.get("specialist_response")
        if isinstance(specialist_response, dict) and specialist_response.get("agent_name") == "logistics_agent":
            return specialist_response

        return None

    def _safe_handoff_v2_apply(payload):
        if not isinstance(payload, dict):
            return payload

        current = payload.get("handoff_payload")
        if isinstance(current, dict) and current:
            return payload

        logistics_input = payload.get("logistics_input")
        if not isinstance(logistics_input, dict):
            logistics_input = {}

        logistics = _safe_handoff_v2_get_logistics(payload)
        nested_handoff = {}
        if isinstance(logistics, dict) and isinstance(logistics.get("handoff_payload"), dict):
            nested_handoff = logistics.get("handoff_payload") or {}

        handoff = {}
        handoff.update(nested_handoff)
        handoff.update({k: v for k, v in logistics_input.items() if v is not None})

        metrics = payload.get("logistics_metrics")
        if isinstance(metrics, dict):
            if metrics.get("total_cbm") is not None:
                handoff["total_cbm"] = metrics.get("total_cbm")
            if metrics.get("total_weight_kg") is not None:
                handoff["total_weight_kg"] = metrics.get("total_weight_kg")
            if metrics.get("recommended_container") is not None:
                handoff["recommended_container"] = metrics.get("recommended_container")
                handoff["container_recommendation"] = metrics.get("recommended_container")
            if metrics.get("risk_level") is not None:
                handoff["risk_level"] = metrics.get("risk_level")
            if metrics.get("risk_score") is not None:
                handoff["risk_score"] = metrics.get("risk_score")

        destination = (
            handoff.get("destination")
            or handoff.get("destination_country")
            or handoff.get("country_to")
            or logistics_input.get("destination")
            or logistics_input.get("destination_country")
            or logistics_input.get("country_to")
        )

        origin = (
            handoff.get("origin")
            or handoff.get("origin_country")
            or handoff.get("country_from")
            or logistics_input.get("origin")
            or logistics_input.get("origin_country")
            or logistics_input.get("country_from")
        )

        if destination:
            handoff["destination"] = destination
            handoff["destination_country"] = destination
            handoff["country_to"] = destination

        if origin:
            handoff["origin"] = origin
            handoff["origin_country"] = origin
            handoff["country_from"] = origin

        if handoff:
            payload["handoff_payload"] = handoff

        return payload

    def cleanup_frontend_response(payload, original_text=None):
        cleaned = _cleanup_frontend_response_before_safe_handoff_v2(payload, original_text)
        try:
            return _safe_handoff_v2_apply(cleaned)
        except Exception:
            return cleaned

except Exception:
    pass


# Handoff route extraction from original text v3.
try:
    import re as _handoff_route_re

    _cleanup_frontend_response_before_handoff_route_v3 = cleanup_frontend_response

    def _handoff_route_v3_clean_country(value):
        raw = str(value or "").strip()
        aliases = {
            "usa": "USA",
            "us": "USA",
            "u.s.": "USA",
            "u.s.a.": "USA",
            "united states": "USA",
            "united states of america": "USA",
            "uk": "UK",
            "united kingdom": "UK",
            "uae": "UAE",
            "turkiye": "Turkey",
        }
        return aliases.get(raw.lower(), raw[:1].upper() + raw[1:] if raw else None)

    def _handoff_route_v3_extract_destination(original_text):
        raw = str(original_text or "")
        countries = (
            r"USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|"
            r"India|Germany|UK|United Kingdom|China|Turkey|Turkiye|UAE|Iran|"
            r"Zambia|Finland|Spain|Portugal|France|Italy|Canada|Mexico|Japan|"
            r"Singapore|Australia|Netherlands|Belgium|Sweden|Norway|Denmark"
        )

        patterns = [
            rf"\b(?:destination|dest|destination_country|country_to)\s*(?:is|=|:)?\s*({countries})\b",
            rf"\bto\s+({countries})\b",
            rf"\binto\s+({countries})\b",
        ]

        for pattern in patterns:
            match = _handoff_route_re.search(pattern, raw, flags=_handoff_route_re.IGNORECASE)
            if match:
                return _handoff_route_v3_clean_country(match.group(1))

        return None

    def _handoff_route_v3_extract_origin(original_text):
        raw = str(original_text or "")
        countries = (
            r"USA|US|U\.S\.|U\.S\.A\.|United States|United States of America|"
            r"India|Germany|UK|United Kingdom|China|Turkey|Turkiye|UAE|Iran|"
            r"Zambia|Finland|Spain|Portugal|France|Italy|Canada|Mexico|Japan|"
            r"Singapore|Australia|Netherlands|Belgium|Sweden|Norway|Denmark"
        )

        match = _handoff_route_re.search(rf"\bfrom\s+({countries})\b", raw, flags=_handoff_route_re.IGNORECASE)
        if match:
            return _handoff_route_v3_clean_country(match.group(1))

        return None

    def _handoff_route_v3_apply(payload, original_text=None):
        if not isinstance(payload, dict):
            return payload

        handoff = payload.get("handoff_payload")
        if not isinstance(handoff, dict):
            handoff = {}

        destination = (
            handoff.get("destination")
            or handoff.get("destination_country")
            or handoff.get("country_to")
            or _handoff_route_v3_extract_destination(original_text)
        )

        origin = (
            handoff.get("origin")
            or handoff.get("origin_country")
            or handoff.get("country_from")
            or _handoff_route_v3_extract_origin(original_text)
        )

        if destination:
            handoff["destination"] = destination
            handoff["destination_country"] = destination
            handoff["country_to"] = destination

        if origin:
            handoff["origin"] = origin
            handoff["origin_country"] = origin
            handoff["country_from"] = origin

        if handoff:
            payload["handoff_payload"] = handoff

        return payload

    def cleanup_frontend_response(payload, original_text=None):
        cleaned = _cleanup_frontend_response_before_handoff_route_v3(payload, original_text)
        try:
            return _handoff_route_v3_apply(cleaned, original_text)
        except Exception:
            return cleaned

except Exception:
    pass


# Finance landed-cost text input cleanup v1.
try:
    import re as _finance_cleanup_re

    _cleanup_frontend_response_before_finance_landed_cost_v1 = cleanup_frontend_response

    def _finance_landed_cost_v1_number(value):
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return None

    def _finance_landed_cost_v1_extract(original_text):
        text = str(original_text or "")
        fields = {}

        patterns = {
            "procurement_value_usd": [
                r"\bprocurement\s+value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bprocurement\s+cost\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bdeclared\s+(?:cargo\s+)?value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bcargo\s+value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bcommercial\s+value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "freight_quote_usd": [
                r"\bfreight\s+quote\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bfreight\s+cost\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "insurance_premium_usd": [
                r"\binsurance\s*(?:premium|cost|quote)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "duty_rate_percent": [
                r"\bduty\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
            ],
            "import_tax_rate_percent": [
                r"\bimport\s+tax\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
                r"\bvat\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
            ],
            "customs_brokerage_usd": [
                r"\bcustoms\s+brokerage\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bbrokerage\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bclearance\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "local_delivery_usd": [
                r"\blocal\s+delivery\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\blast[-\s]?mile\s+delivery\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bdestination\s+delivery\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
        }

        for key, key_patterns in patterns.items():
            for pattern in key_patterns:
                match = _finance_cleanup_re.search(pattern, text, flags=_finance_cleanup_re.IGNORECASE)
                if match:
                    value = _finance_landed_cost_v1_number(match.group(1))
                    if value is not None:
                        fields[key] = value
                        break

        if fields.get("procurement_value_usd") is not None:
            fields["declared_value_usd"] = fields["procurement_value_usd"]
            fields["commercial_value_usd"] = fields["procurement_value_usd"]

        return fields

    def _finance_landed_cost_v1_filter_missing(items, known_fields):
        if not isinstance(items, list):
            return []

        aliases = {
            "procurement_value_usd": ["procurement value", "declared value", "cargo value", "commercial value"],
            "customs_brokerage_usd": ["customs brokerage", "brokerage", "clearance"],
            "local_delivery_usd": ["local delivery", "last-mile", "last mile", "destination delivery"],
            "freight_quote_usd": ["freight"],
            "insurance_premium_usd": ["insurance"],
            "duty_rate_percent": ["duty"],
            "import_tax_rate_percent": ["import tax", "vat"],
        }

        filtered = []
        for item in items:
            lowered = str(item or "").lower()
            remove = False
            for field, tokens in aliases.items():
                if field in known_fields and any(token in lowered for token in tokens):
                    remove = True
                    break
            if not remove:
                filtered.append(item)

        return filtered

    def _finance_landed_cost_v1_calculate(known):
        procurement = _finance_landed_cost_v1_number(known.get("procurement_value_usd"))
        freight = _finance_landed_cost_v1_number(known.get("freight_quote_usd")) or 0.0
        insurance = _finance_landed_cost_v1_number(known.get("insurance_premium_usd")) or 0.0
        duty_rate = _finance_landed_cost_v1_number(known.get("duty_rate_percent")) or 0.0
        tax_rate = _finance_landed_cost_v1_number(known.get("import_tax_rate_percent")) or 0.0
        brokerage = _finance_landed_cost_v1_number(known.get("customs_brokerage_usd")) or 0.0
        local_delivery = _finance_landed_cost_v1_number(known.get("local_delivery_usd")) or 0.0

        if procurement is None:
            return None

        customs_value = procurement + freight + insurance
        estimated_duty = customs_value * duty_rate / 100.0
        import_tax_base = customs_value + estimated_duty
        estimated_import_tax = import_tax_base * tax_rate / 100.0
        landed_cost = procurement + freight + insurance + estimated_duty + estimated_import_tax + brokerage + local_delivery

        return {
            "customs_value_usd": round(customs_value, 2),
            "estimated_duty_usd": round(estimated_duty, 2),
            "import_tax_base_usd": round(import_tax_base, 2),
            "estimated_import_tax_usd": round(estimated_import_tax, 2),
            "estimated_subtotal_known_usd": round(landed_cost, 2),
            "estimated_landed_cost_usd": round(landed_cost, 2),
            "landed_cost_formula": [
                "procurement_value_usd",
                "freight_quote_usd",
                "insurance_premium_usd",
                "estimated_duty",
                "estimated_import_tax_or_vat",
                "customs_brokerage_usd",
                "local_delivery_usd",
            ],
        }

    def _finance_landed_cost_v1_apply(payload, original_text=None):
        if not isinstance(payload, dict):
            return payload

        extracted = _finance_landed_cost_v1_extract(original_text)
        if not extracted:
            return payload

        finance_payload = payload.get("finance_payload")
        if not isinstance(finance_payload, dict):
            finance_payload = {}

        for key, value in extracted.items():
            payload[key] = value
            finance_payload[key] = value

        payload["finance_payload"] = finance_payload

        advice = payload.get("landed_cost_advice")
        if not isinstance(advice, dict):
            advice = {
                "applicable": True,
                "status": "review_required",
                "summary": "Landed cost advice prepared from finance inputs.",
                "known_inputs": {},
                "missing_cost_inputs": [],
                "blockers": [],
                "warnings": [],
                "recommendations": [],
            }

        known_inputs = advice.get("known_inputs")
        if not isinstance(known_inputs, dict):
            known_inputs = {}

        for key, value in extracted.items():
            if key in {"declared_value_usd", "commercial_value_usd"}:
                continue
            known_inputs[key] = value

        advice["known_inputs"] = known_inputs

        known_fields = {key for key, value in known_inputs.items() if value is not None}
        advice["missing_cost_inputs"] = _finance_landed_cost_v1_filter_missing(
            advice.get("missing_cost_inputs") or [],
            known_fields,
        )

        blockers = []
        for blocker in advice.get("blockers") or []:
            lowered = str(blocker or "").lower()
            if "procurement value" in lowered and "procurement_value_usd" in known_fields:
                continue
            if "declared value" in lowered and "procurement_value_usd" in known_fields:
                continue
            blockers.append(blocker)
        advice["blockers"] = blockers

        calculation = _finance_landed_cost_v1_calculate(known_inputs)
        if calculation:
            advice.update(calculation)

        if not advice.get("missing_cost_inputs") and not advice.get("blockers"):
            advice["status"] = "review_required"
            advice["summary"] = "Landed cost advice prepared from the supplied finance inputs."
            recommendations = advice.get("recommendations")
            if not isinstance(recommendations, list):
                recommendations = []
            recommendations.append("Validate freight quote, insurance premium, duty rate, import tax, brokerage, and local delivery before final booking.")
            advice["recommendations"] = list(dict.fromkeys(str(item) for item in recommendations if item))

        payload["landed_cost_advice"] = advice

        return payload

    def cleanup_frontend_response(payload, original_text=None):
        cleaned = _cleanup_frontend_response_before_finance_landed_cost_v1(payload, original_text)
        try:
            return _finance_landed_cost_v1_apply(cleaned, original_text)
        except Exception:
            return cleaned

except Exception:
    pass


# Finance landed-cost text input cleanup v2.
try:
    import json as _finance_v2_json
    import re as _finance_v2_re

    _cleanup_frontend_response_before_finance_landed_cost_v2 = cleanup_frontend_response

    def _finance_v2_as_number(value):
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return None

    def _finance_v2_source_text(payload, original_text=None):
        parts = []

        if original_text:
            parts.append(str(original_text))

        try:
            from app.request_context import active_request_text
            active_text = active_request_text()
            if active_text:
                parts.append(str(active_text))
        except Exception:
            pass

        if isinstance(payload, dict):
            for key in ["user_text", "request_text", "text", "prompt", "original_text"]:
                value = payload.get(key)
                if value:
                    parts.append(str(value))

            metadata = payload.get("request_metadata")
            if isinstance(metadata, dict):
                for key in ["user_text", "request_text", "text", "prompt", "original_text"]:
                    value = metadata.get(key)
                    if value:
                        parts.append(str(value))

            try:
                parts.append(_finance_v2_json.dumps(payload, default=str))
            except Exception:
                pass

        return "\n".join(part for part in parts if part)

    def _finance_v2_extract_fields(payload, original_text=None):
        source = _finance_v2_source_text(payload, original_text)
        fields = {}

        patterns = {
            "procurement_value_usd": [
                r"\bprocurement\s+value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bprocurement\s+cost\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bdeclared\s+(?:cargo\s+)?value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bcargo\s+value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bcommercial\s+value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "freight_quote_usd": [
                r"\bfreight\s+quote\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bfreight\s+cost\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "insurance_premium_usd": [
                r"\binsurance\s*(?:premium|cost|quote)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "duty_rate_percent": [
                r"\bduty\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
            ],
            "import_tax_rate_percent": [
                r"\bimport\s+tax\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
                r"\bvat\s*(?:rate)?\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(?:%|percent|per\s+cent)\b",
            ],
            "customs_brokerage_usd": [
                r"\bcustoms\s+brokerage\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bbrokerage\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bclearance\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
            "local_delivery_usd": [
                r"\blocal\s+delivery\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\blast[-\s]?mile\s+delivery\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
                r"\bdestination\s+delivery\s*(?:fee|cost)?\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
            ],
        }

        for key, key_patterns in patterns.items():
            for pattern in key_patterns:
                match = _finance_v2_re.search(pattern, source, flags=_finance_v2_re.IGNORECASE)
                if match:
                    number = _finance_v2_as_number(match.group(1))
                    if number is not None:
                        fields[key] = number
                        break

        if "procurement_value_usd" in fields:
            fields["declared_value_usd"] = fields["procurement_value_usd"]
            fields["commercial_value_usd"] = fields["procurement_value_usd"]

        return fields

    def _finance_v2_calculate(known):
        procurement = _finance_v2_as_number(known.get("procurement_value_usd"))
        if procurement is None:
            return {}

        freight = _finance_v2_as_number(known.get("freight_quote_usd")) or 0.0
        insurance = _finance_v2_as_number(known.get("insurance_premium_usd")) or 0.0
        duty_rate = _finance_v2_as_number(known.get("duty_rate_percent")) or 0.0
        tax_rate = _finance_v2_as_number(known.get("import_tax_rate_percent")) or 0.0
        brokerage = _finance_v2_as_number(known.get("customs_brokerage_usd")) or 0.0
        local_delivery = _finance_v2_as_number(known.get("local_delivery_usd")) or 0.0

        customs_value = procurement + freight + insurance
        duty = customs_value * duty_rate / 100.0
        import_tax_base = customs_value + duty
        import_tax = import_tax_base * tax_rate / 100.0
        landed = procurement + freight + insurance + duty + import_tax + brokerage + local_delivery

        return {
            "customs_value_usd": round(customs_value, 2),
            "estimated_duty_usd": round(duty, 2),
            "import_tax_base_usd": round(import_tax_base, 2),
            "estimated_import_tax_usd": round(import_tax, 2),
            "estimated_subtotal_known_usd": round(landed, 2),
            "estimated_landed_cost_usd": round(landed, 2),
            "landed_cost_formula": [
                "procurement_value_usd",
                "freight_quote_usd",
                "insurance_premium_usd",
                "estimated_duty",
                "estimated_import_tax_or_vat",
                "customs_brokerage_usd",
                "local_delivery_usd",
            ],
        }

    def _finance_v2_filter_list(items, known_fields):
        if not isinstance(items, list):
            return []

        token_map = {
            "procurement_value_usd": ["procurement_value_usd", "procurement value", "declared value", "cargo value", "commercial value"],
            "customs_brokerage_usd": ["customs_brokerage_usd", "customs brokerage", "brokerage", "clearance"],
            "local_delivery_usd": ["local_delivery_usd", "local delivery", "last mile", "last-mile", "destination delivery"],
            "freight_quote_usd": ["freight_quote_usd", "freight quote", "freight cost"],
            "insurance_premium_usd": ["insurance_premium_usd", "insurance premium", "insurance cost"],
            "duty_rate_percent": ["duty_rate_percent", "duty rate"],
            "import_tax_rate_percent": ["import_tax_rate_percent", "import tax", "vat"],
        }

        filtered = []
        for item in items:
            lowered = str(item or "").lower()
            remove = False
            for field in known_fields:
                for token in token_map.get(field, []):
                    if token in lowered:
                        remove = True
                        break
                if remove:
                    break
            if not remove:
                filtered.append(item)

        return filtered

    def _finance_v2_recursive_filter(obj, known_fields):
        if isinstance(obj, dict):
            return {key: _finance_v2_recursive_filter(value, known_fields) for key, value in obj.items()}

        if isinstance(obj, list):
            filtered = _finance_v2_filter_list(obj, known_fields)
            return [_finance_v2_recursive_filter(item, known_fields) for item in filtered]

        return obj

    def _finance_v2_apply(payload, original_text=None):
        if not isinstance(payload, dict):
            return payload

        fields = _finance_v2_extract_fields(payload, original_text)
        if not fields:
            return payload

        finance_payload = payload.get("finance_payload")
        if not isinstance(finance_payload, dict):
            finance_payload = {}

        for key, value in fields.items():
            payload[key] = value
            finance_payload[key] = value

        payload["finance_payload"] = finance_payload

        advice = payload.get("landed_cost_advice")
        if not isinstance(advice, dict):
            advice = {}

        advice.setdefault("applicable", True)
        known = advice.get("known_inputs")
        if not isinstance(known, dict):
            known = {}

        for key, value in fields.items():
            if key in {"declared_value_usd", "commercial_value_usd"}:
                continue
            known[key] = value

        advice["known_inputs"] = known

        known_fields = {key for key, value in known.items() if value is not None}

        advice["missing_cost_inputs"] = _finance_v2_filter_list(advice.get("missing_cost_inputs") or [], known_fields)
        advice["blockers"] = _finance_v2_filter_list(advice.get("blockers") or [], known_fields)
        advice["warnings"] = _finance_v2_filter_list(advice.get("warnings") or [], known_fields)
        advice["recommendations"] = _finance_v2_filter_list(advice.get("recommendations") or [], known_fields)

        calculation = _finance_v2_calculate(known)
        if calculation:
            advice.update(calculation)

        if not advice.get("missing_cost_inputs") and not advice.get("blockers"):
            advice["status"] = "review_required"
            advice["summary"] = "Landed cost advice prepared from the supplied finance inputs."
            recommendations = advice.get("recommendations")
            if not isinstance(recommendations, list):
                recommendations = []
            recommendations.append("Validate all supplied finance inputs before final booking.")
            advice["recommendations"] = list(dict.fromkeys(str(item) for item in recommendations if item))

        payload["landed_cost_advice"] = advice

        # Remove stale missing-field prompts from action_plan, booking_readiness, summaries, etc.
        payload = _finance_v2_recursive_filter(payload, known_fields)
        payload["landed_cost_advice"] = advice
        payload["finance_payload"] = finance_payload

        return payload

    def cleanup_frontend_response(payload, original_text=None):
        cleaned = _cleanup_frontend_response_before_finance_landed_cost_v2(payload, original_text)
        try:
            return _finance_v2_apply(cleaned, original_text)
        except Exception:
            return cleaned

except Exception:
    pass


# Backend response polish hook v1.
try:
    from app.backend_response_polish import polish_backend_response as _backend_response_polish_v1

    _cleanup_frontend_response_before_backend_response_polish_v1 = cleanup_frontend_response

    def cleanup_frontend_response(payload, original_text=None):
        cleaned = _cleanup_frontend_response_before_backend_response_polish_v1(payload, original_text)
        try:
            return _backend_response_polish_v1(cleaned, original_text)
        except Exception:
            return cleaned

except Exception:
    pass

