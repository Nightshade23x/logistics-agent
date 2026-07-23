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

