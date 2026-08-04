# FRONTEND RESPONSE CLEANUP
# This is the final formatting layer before the response reaches the frontend.
# It keeps calculations consistent while preserving user-facing units.

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

# Final frontend response repair v11.
try:
    from app.final_text_response_fixes import (
        repair_frontend_payload as _repair_frontend_payload_v11,
    )

    _cleanup_frontend_response_before_final_v11 = (
        cleanup_frontend_response
    )

    def cleanup_frontend_response(
        payload,
        original_text=None,
    ):
        cleaned = (
            _cleanup_frontend_response_before_final_v11(
                payload,
                original_text,
            )
        )

        return _repair_frontend_payload_v11(
            cleaned,
            original_text,
        )

except Exception:
    pass

# FINALIZED_BACKEND_PAYLOAD_IDEMPOTENCY_V20
#
# api_server.py runs cleanup_frontend_response as HTTP middleware after the
# backend_service route has already produced its final frontend payload.
# Re-running the historical cleanup chain can reinterpret authoritative cargo
# totals. Final backend_service payloads are therefore returned unchanged.
# Direct/specialist payloads without the backend_service marker still use the
# existing cleanup chain.

_cleanup_frontend_response_before_idempotency_v20 = (
    cleanup_frontend_response
)


def _v20_is_final_backend_service_payload(payload):
    if not isinstance(payload, dict):
        return False

    metadata = payload.get("request_metadata")

    if not isinstance(metadata, dict):
        return False

    if metadata.get("served_by") != "backend_service":
        return False

    metrics = payload.get("logistics_metrics")
    visualizer = payload.get("logistics_visualizer")

    return (
        isinstance(metrics, dict)
        or isinstance(visualizer, dict)
        or payload.get("backend_validation") is not None
    )


def cleanup_frontend_response(payload, original_text=None):
    if _v20_is_final_backend_service_payload(payload):
        return payload

    return _cleanup_frontend_response_before_idempotency_v20(
        payload,
        original_text,
    )

# DYNAMIC_COMPLIANCE_DOCS_V65_FINAL_CLEANUP_HOOK
# Run deterministic compliance/document enrichment after all existing
# cleanup and polish wrappers, so the API payload and React ui_sections
# receive the same final values.
try:
    from app.dynamic_compliance_enrichment import (
        enrich_dynamic_compliance_payload as _dynamic_compliance_docs_v65_final,
    )

    _cleanup_frontend_response_before_dynamic_compliance_docs_v65 = (
        cleanup_frontend_response
    )

    def cleanup_frontend_response(payload, original_text=None):
        cleaned = (
            _cleanup_frontend_response_before_dynamic_compliance_docs_v65(
                payload,
                original_text,
            )
        )
        return _dynamic_compliance_docs_v65_final(
            cleaned,
            original_text,
        )

except Exception:
    pass

# FLEXIBLE_DISPLAY_UNITS_V67
# Preserve requested display units while keeping kg/CBM internally.
import re as _v67_re

_cleanup_frontend_response_before_flexible_units_v67 = cleanup_frontend_response


def _v67_num(value):
    try:
        if value in (None, "", True, False):
            return None
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _v67_round(value):
    number = _v67_num(value)
    if number is None:
        return None
    rounded = round(number, 6)
    return int(rounded) if float(rounded).is_integer() else rounded


def _v67_text(payload, original_text=None):
    metadata = payload.get("request_metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    for value in (
        original_text,
        metadata.get("input_source"),
        metadata.get("original_text"),
        metadata.get("request_text"),
        payload.get("original_prompt"),
        payload.get("request_text"),
        payload.get("user_request"),
        payload.get("prompt"),
        payload.get("input_text"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _v67_quantity(text):
    for pattern in (
        r"(?i)\b(?:ship|send|export|import|calculate[^.]{0,80}?for|list[^.]{0,80}?for|find[^.]{0,80}?for)\s+([0-9][0-9,]*)\s+[a-z][a-z0-9 _/-]{0,40}\s+of\b",
        r"(?i)^\s*([0-9][0-9,]*)\s+[a-z][a-z0-9 _/-]{0,40}\s+of\b",
    ):
        match = _v67_re.search(pattern, text)
        if match:
            value = _v67_num(match.group(1))
            if value and value > 0:
                return int(value)
    return None


def _v67_weight_alias(raw):
    value = str(raw or "").strip().lower().rstrip(".")
    return {
        "kg": ("kg", 1.0), "kgs": ("kg", 1.0), "kilogram": ("kg", 1.0), "kilograms": ("kg", 1.0),
        "g": ("g", 0.001), "gram": ("g", 0.001), "grams": ("g", 0.001),
        "t": ("tonnes", 1000.0), "tonne": ("tonnes", 1000.0), "tonnes": ("tonnes", 1000.0),
        "metric ton": ("tonnes", 1000.0), "metric tons": ("tonnes", 1000.0),
        "lb": ("lb", 0.45359237), "lbs": ("lb", 0.45359237), "llb": ("lb", 0.45359237),
        "llbs": ("lb", 0.45359237), "pound": ("lb", 0.45359237), "pounds": ("lb", 0.45359237),
        "oz": ("oz", 0.028349523125), "ounce": ("oz", 0.028349523125), "ounces": ("oz", 0.028349523125),
        "st": ("st", 6.35029318), "stone": ("st", 6.35029318), "stones": ("st", 6.35029318),
    }.get(value)


def _v67_weight(text):
    quantity = _v67_quantity(text)

    custom = _v67_re.search(
        r"(?i)\boriginal\s+package\s+weight\s*:\s*([0-9][0-9,.]*)\s+([a-z][a-z0-9 _/-]{0,40})\s*[.;]",
        text,
    )
    if custom:
        value = _v67_num(custom.group(1))
        unit = str(custom.group(2)).strip()
        if value is not None and unit:
            return {
                "source": "original_package_weight",
                "unit_weight": _v67_round(value),
                "display_unit": unit,
                "package_count": quantity,
                "total_weight": _v67_round(value * quantity) if quantity else None,
                "kg_factor": None,
            }

    total = _v67_re.search(
        r"(?i)\btotal(?:\s+shipment|\s+cargo|\s+load)?\s+weight\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*(kg|kgs?|kilograms?|g|grams?|t|tonnes?|metric\s+tons?|lb|lbs?|llb|llbs?|pounds?|oz|ounces?|st|stones?)\b",
        text,
    )
    if total:
        info = _v67_weight_alias(total.group(2))
        value = _v67_num(total.group(1))
        if info and value is not None:
            return {
                "source": "explicit_total_weight",
                "unit_weight": None,
                "display_unit": info[0],
                "package_count": quantity,
                "total_weight": _v67_round(value),
                "kg_factor": info[1],
            }

    each = _v67_re.search(
        r"(?i)\beach\b[^.;\n]{0,500}?\b(?:weighs?|weight\s*(?:is|=|:))\s*([0-9][0-9,.]*)\s*(kg|kgs?|kilograms?|g|grams?|t|tonnes?|metric\s+tons?|lb|lbs?|llb|llbs?|pounds?|oz|ounces?|st|stones?)\b",
        text,
    )
    if each:
        info = _v67_weight_alias(each.group(2))
        value = _v67_num(each.group(1))
        if info and value is not None:
            return {
                "source": "per_package_weight",
                "unit_weight": _v67_round(value),
                "display_unit": info[0],
                "package_count": quantity,
                "total_weight": _v67_round(value * quantity) if quantity else None,
                "kg_factor": info[1],
            }
    return None


def _v67_volume_alias(raw):
    value = str(raw or "").strip().lower().rstrip(".")
    return {
        "cbm": ("CBM", 1.0), "m3": ("CBM", 1.0), "m^3": ("CBM", 1.0),
        "cubic metre": ("CBM", 1.0), "cubic metres": ("CBM", 1.0),
        "cubic meter": ("CBM", 1.0), "cubic meters": ("CBM", 1.0),
        "l": ("L", 0.001), "litre": ("L", 0.001), "litres": ("L", 0.001),
        "liter": ("L", 0.001), "liters": ("L", 0.001),
        "ml": ("mL", 0.000001), "millilitre": ("mL", 0.000001), "millilitres": ("mL", 0.000001),
        "milliliter": ("mL", 0.000001), "milliliters": ("mL", 0.000001),
        "ft3": ("ft³", 0.028316846592), "ft^3": ("ft³", 0.028316846592),
        "cubic foot": ("ft³", 0.028316846592), "cubic feet": ("ft³", 0.028316846592),
        "in3": ("in³", 0.000016387064), "in^3": ("in³", 0.000016387064),
        "cubic inch": ("in³", 0.000016387064), "cubic inches": ("in³", 0.000016387064),
    }.get(value)


def _v67_volume(text):
    quantity = _v67_quantity(text)
    match = _v67_re.search(
        r"(?i)\boriginal\s+package\s+volume\s*:\s*([0-9][0-9,.]*)\s+([a-z][a-z0-9³^ _/-]{0,40})\s*[.;]",
        text,
    )
    if not match:
        return None
    value = _v67_num(match.group(1))
    raw_unit = str(match.group(2)).strip()
    known = _v67_volume_alias(raw_unit)
    if value is None or not raw_unit:
        return None
    return {
        "source": "original_package_volume",
        "unit_volume": _v67_round(value),
        "display_unit": known[0] if known else raw_unit,
        "package_count": quantity,
        "total_volume": _v67_round(value * quantity) if quantity else None,
        "cbm_factor": known[1] if known else None,
    }


def _v67_sync_weight(payload, display):
    """Synchronise user-facing weight units with internal kilograms.

    The final backend wrapper supplies the original request text, so pounds,
    ounces, tonnes and custom units remain visible even after older backend
    stages normalise calculations to kilograms.
    """
    if not isinstance(payload, dict) or not isinstance(display, dict):
        return

    unit_display = _v67_num(display.get("unit_weight"))
    package_count = _v67_num(display.get("package_count"))
    total_display = _v67_num(display.get("total_weight"))

    if (
        total_display is None
        and unit_display is not None
        and package_count is not None
        and package_count > 0
    ):
        total_display = unit_display * package_count
        display["total_weight"] = _v67_round(total_display)

    factor = _v67_num(display.get("kg_factor"))
    calculated_kg = (
        total_display * factor
        if total_display is not None and factor is not None
        else None
    )

    metrics = payload.get("logistics_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
        payload["logistics_metrics"] = metrics

    handoff = payload.get("handoff_payload")
    review = payload.get("logistics_quality_review")
    visualizer = payload.get("logistics_visualizer")
    container = (
        visualizer.get("container")
        if isinstance(visualizer, dict)
        and isinstance(visualizer.get("container"), dict)
        else None
    )

    candidates = (
        calculated_kg,
        _v67_num(metrics.get("total_weight_kg")),
        _v67_num(handoff.get("total_weight_kg"))
        if isinstance(handoff, dict)
        else None,
        _v67_num(review.get("total_weight_kg"))
        if isinstance(review, dict)
        else None,
        _v67_num(container.get("total_weight_kg"))
        if isinstance(container, dict)
        else None,
    )

    total_kg = next(
        (
            value
            for value in candidates
            if value is not None and value >= 0
        ),
        None,
    )

    display_measurements = payload.get("display_measurements")
    if not isinstance(display_measurements, dict):
        display_measurements = {}
        payload["display_measurements"] = display_measurements

    display_measurements["weight"] = display

    display_total = (
        _v67_round(total_display)
        if total_display is not None
        else display.get("total_weight")
    )
    display_unit = display.get("display_unit")

    if total_kg is None:
        # A custom unit can still be displayed even when no conversion factor
        # was supplied. The shipment remains incomplete for payload checks.
        metrics.update(
            {
                "display_total_weight": display_total,
                "display_weight_unit": display_unit,
            }
        )
        return

    total_kg = _v67_round(total_kg)
    if total_kg is None:
        return

    metrics.update(
        {
            "total_weight_kg": total_kg,
            "weight_known": True,
            "display_total_weight": display_total,
            "display_weight_unit": display_unit,
        }
    )

    for key in (
        "handoff_payload",
        "logistics_quality_review",
    ):
        section = payload.get(key)
        if isinstance(section, dict):
            section.update(
                {
                    "total_weight_kg": total_kg,
                    "weight_known": True,
                    "display_total_weight": display_total,
                    "display_weight_unit": display_unit,
                }
            )

    executive = payload.get("executive_summary")
    if (
        isinstance(executive, dict)
        and isinstance(
            executive.get("shipment_snapshot"),
            dict,
        )
    ):
        executive["shipment_snapshot"].update(
            {
                "total_weight_kg": total_kg,
                "display_total_weight": display_total,
                "display_weight_unit": display_unit,
            }
        )

    if not isinstance(visualizer, dict):
        return

    container = visualizer.get("container")
    if not isinstance(container, dict):
        container = {}
        visualizer["container"] = container

    container.update(
        {
            "total_weight_kg": total_kg,
            "weight_known": True,
            "display_total_weight": display_total,
            "display_weight_unit": display_unit,
        }
    )

    display_metrics = visualizer.get("display_metrics")
    if isinstance(display_metrics, dict):
        display_metrics.update(
            {
                "total_weight_kg": total_kg,
                "display_total_weight": display_total,
                "display_weight_unit": display_unit,
            }
        )

    cargo = visualizer.get("cargo_mix")
    if (
        isinstance(cargo, list)
        and len(cargo) == 1
        and isinstance(cargo[0], dict)
    ):
        quantity = (
            _v67_num(cargo[0].get("quantity"))
            or package_count
            or 1
        )
        if quantity <= 0:
            quantity = 1

        cargo[0].update(
            {
                "total_weight_kg": total_kg,
                "unit_weight_kg": _v67_round(
                    float(total_kg) / quantity
                ),
                "display_total_weight": display_total,
                "display_unit_weight": display.get(
                    "unit_weight"
                ),
                "display_weight_unit": display_unit,
                "weight_known": True,
            }
        )

    sections = payload.get("ui_sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            if section.get("section_id") not in {
                "logistics",
                "container_planning",
            }:
                continue

            section_metrics = section.get("metrics")
            if not isinstance(section_metrics, dict):
                section_metrics = {}
                section["metrics"] = section_metrics

            section_metrics.update(
                {
                    "total_weight_kg": total_kg,
                    "display_total_weight": display_total,
                    "display_weight_unit": display_unit,
                }
            )


def _v67_sync_volume(payload, display, text):
    """Synchronise direct-volume display data without ever replacing valid
    internal CBM with None.

    V67 may run more than once in the response-cleanup chain. On a later pass,
    the original display clause can be incomplete while the payload already
    contains a valid CBM total. This function therefore resolves the total from
    every trustworthy source before updating the payload.
    """
    if not isinstance(payload, dict) or not isinstance(display, dict):
        return

    total_display = _v67_num(display.get("total_volume"))
    unit_display = _v67_num(display.get("unit_volume"))
    package_count = _v67_num(display.get("package_count"))

    if (
        total_display is None
        and unit_display is not None
        and package_count is not None
        and package_count > 0
    ):
        total_display = unit_display * package_count
        display["total_volume"] = _v67_round(total_display)

    factor = _v67_num(display.get("cbm_factor"))
    calculated_cbm = (
        total_display * factor
        if total_display is not None and factor is not None
        else None
    )

    explicit_total = None
    for pattern in (
        r"(?i)\btotal\s+shipment\s+volume\s+is\s+([0-9][0-9,.]*)\s*CBM\b",
        r"(?i)\b([0-9][0-9,.]*)\s*CBM\s+of\b",
    ):
        match = _v67_re.search(pattern, str(text or ""))
        if match:
            explicit_total = _v67_num(match.group(1))
            if explicit_total is not None:
                break

    metrics = payload.get("logistics_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
        payload["logistics_metrics"] = metrics

    handoff = payload.get("handoff_payload")
    review = payload.get("logistics_quality_review")
    visualizer = payload.get("logistics_visualizer")
    container = (
        visualizer.get("container")
        if isinstance(visualizer, dict)
        and isinstance(visualizer.get("container"), dict)
        else None
    )

    candidates = (
        calculated_cbm,
        explicit_total,
        _v67_num(metrics.get("total_cbm")),
        _v67_num(handoff.get("total_cbm")) if isinstance(handoff, dict) else None,
        _v67_num(review.get("total_cbm")) if isinstance(review, dict) else None,
        _v67_num(container.get("total_cbm")) if isinstance(container, dict) else None,
    )

    total_cbm = next(
        (
            value
            for value in candidates
            if value is not None and value >= 0
        ),
        None,
    )

    if total_cbm is None:
        return

    total_cbm = _v67_round(total_cbm)
    if total_cbm is None:
        return

    display_total = (
        _v67_round(total_display)
        if total_display is not None
        else display.get("total_volume")
    )
    display_unit = display.get("display_unit")

    metrics.update(
        {
            "total_cbm": total_cbm,
            "display_total_volume": display_total,
            "display_volume_unit": display_unit,
        }
    )

    for key in ("handoff_payload", "logistics_quality_review"):
        section = payload.get(key)
        if isinstance(section, dict):
            section.update(
                {
                    "total_cbm": total_cbm,
                    "display_total_volume": display_total,
                    "display_volume_unit": display_unit,
                }
            )

    executive = payload.get("executive_summary")
    if (
        isinstance(executive, dict)
        and isinstance(executive.get("shipment_snapshot"), dict)
    ):
        executive["shipment_snapshot"].update(
            {
                "total_cbm": total_cbm,
                "display_total_volume": display_total,
                "display_volume_unit": display_unit,
            }
        )

    if not isinstance(visualizer, dict):
        return

    container = visualizer.get("container")
    if not isinstance(container, dict):
        container = {}
        visualizer["container"] = container

    container.update(
        {
            "total_cbm": total_cbm,
            "display_total_volume": display_total,
            "display_volume_unit": display_unit,
        }
    )

    display_metrics = visualizer.get("display_metrics")
    if isinstance(display_metrics, dict):
        display_metrics.update(
            {
                "total_cbm": total_cbm,
                "loaded_cbm": total_cbm,
                "display_total_volume": display_total,
                "display_volume_unit": display_unit,
            }
        )

    capacity = _v67_num(container.get("capacity_cbm"))
    if capacity is not None and capacity > 0:
        container["utilization_percent"] = round(
            float(total_cbm) / capacity * 100,
            2,
        )
        if isinstance(display_metrics, dict):
            display_metrics["utilization_percent"] = container[
                "utilization_percent"
            ]

    cargo = visualizer.get("cargo_mix")
    if (
        isinstance(cargo, list)
        and len(cargo) == 1
        and isinstance(cargo[0], dict)
    ):
        quantity = (
            _v67_num(cargo[0].get("quantity"))
            or package_count
            or 1
        )
        if quantity <= 0:
            quantity = 1

        cargo[0].update(
            {
                "total_cbm": total_cbm,
                "unit_cbm": _v67_round(float(total_cbm) / quantity),
                "display_total_volume": display_total,
                "display_unit_volume": display.get("unit_volume"),
                "display_volume_unit": display_unit,
            }
        )

    sections = payload.get("ui_sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            if section.get("section_id") not in {
                "logistics",
                "container_planning",
            }:
                continue

            section_metrics = section.get("metrics")
            if not isinstance(section_metrics, dict):
                section_metrics = {}
                section["metrics"] = section_metrics

            section_metrics.update(
                {
                    "total_cbm": total_cbm,
                    "display_total_volume": display_total,
                    "display_volume_unit": display_unit,
                }
            )


def cleanup_frontend_response(payload, original_text=None):
    cleaned = _cleanup_frontend_response_before_flexible_units_v67(payload, original_text)
    if not isinstance(cleaned, dict):
        return cleaned
    text = _v67_text(cleaned, original_text)
    if not text:
        return cleaned

    weight = _v67_weight(text)
    volume = _v67_volume(text)
    display = cleaned.get("display_measurements")
    if not isinstance(display, dict):
        display = {}
        cleaned["display_measurements"] = display

    if weight:
        display["weight"] = weight
        _v67_sync_weight(cleaned, weight)
    if volume:
        display["volume"] = volume
        _v67_sync_volume(cleaned, volume, text)

    metadata = cleaned.get("request_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        cleaned["request_metadata"] = metadata
    metadata["flexible_display_units_v67"] = {
        "status": "applied",
        "weight_unit": weight.get("display_unit") if weight else None,
        "volume_unit": volume.get("display_unit") if volume else None,
    }
    return cleaned

# BEGIN FINAL_DISPLAY_UNIT_AUTHORITY_V71
# This wrapper runs after every existing frontend cleanup pass. It restores the
# units from the original request without changing internal kg/CBM calculations.
_final_display_unit_previous_cleanup_v71 = cleanup_frontend_response

_FINAL_NUMBER_V71 = r"[0-9][0-9,]*(?:\.[0-9]+)?"


def _final_number_v71(value):
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _final_round_v71(value):
    number = _final_number_v71(value)
    if number is None:
        return None
    rounded = round(number, 6)
    return int(rounded) if float(rounded).is_integer() else rounded


def _final_original_text_v71(payload, args, kwargs):
    for key in (
        "user_text",
        "text",
        "request_text",
        "prompt",
        "original_text",
    ):
        value = kwargs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for value in args[1:]:
        if isinstance(value, str) and value.strip():
            return value.strip()

    metadata = payload.get("request_metadata")
    if isinstance(metadata, dict):
        for key in (
            "original_input_source",
            "input_source",
            "original_text",
            "request_text",
            "user_text",
            "prompt",
        ):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for key in (
        "original_prompt",
        "request_text",
        "user_request",
        "prompt",
        "input_text",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _final_quantity_v71(text):
    patterns = (
        rf"(?i)\b(?:ship|send|move|transport|deliver|export|import)\s+"
        rf"({_FINAL_NUMBER_V71})\s+"
        rf"(?:packages?|boxes?|cartons?|crates?|pallets?|bags?|drums?|"
        rf"bottles?|barrels?|bundles?|sacks?|cases?|units?|pieces?|pcs?)\b",
        rf"(?i)\b({_FINAL_NUMBER_V71})\s+"
        rf"(?:packages?|boxes?|cartons?|crates?|pallets?|bags?|drums?|"
        rf"bottles?|barrels?|bundles?|sacks?|cases?|units?|pieces?|pcs?)\s+of\b",
    )

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            quantity = _final_number_v71(match.group(1))
            if quantity is not None and quantity > 0:
                return quantity

    return 1.0


def _final_weight_unit_v71(raw_unit):
    key = re.sub(r"[^a-z0-9]+", "", str(raw_unit or "").lower())

    mapping = {
        "lb": ("lb", 0.45359237),
        "lbs": ("lb", 0.45359237),
        "llb": ("lb", 0.45359237),
        "llbs": ("lb", 0.45359237),
        "pound": ("lb", 0.45359237),
        "pounds": ("lb", 0.45359237),
        "kg": ("kg", 1.0),
        "kgs": ("kg", 1.0),
        "kilogram": ("kg", 1.0),
        "kilograms": ("kg", 1.0),
        "g": ("g", 0.001),
        "gram": ("g", 0.001),
        "grams": ("g", 0.001),
        "oz": ("oz", 0.028349523125),
        "ounce": ("oz", 0.028349523125),
        "ounces": ("oz", 0.028349523125),
        "st": ("st", 6.35029318),
        "stone": ("st", 6.35029318),
        "stones": ("st", 6.35029318),
        "t": ("t", 1000.0),
        "tonne": ("t", 1000.0),
        "tonnes": ("t", 1000.0),
        "metricton": ("t", 1000.0),
        "metrictons": ("t", 1000.0),
        "ton": ("ton", 907.18474),
        "tons": ("ton", 907.18474),
    }

    return mapping.get(key, (None, None))


# READ ORIGINAL WEIGHT UNIT
# Reads the original request and extracts the display weight unit.
# Example: 10 crates at 250 lb becomes 2500 lb for display.

def _final_weight_v71(text):
    quantity = _final_quantity_v71(text)
    unit_pattern = (
        r"(llbs?|lbs?|pounds?|kgs?|kilograms?|kg|grams?|g|"
        r"tonnes?|metric\s+tons?|tons?|t|ounces?|oz|stones?|st)"
    )

    per_package_patterns = (
        rf"(?is)\beach\b.{{0,260}}?"
        rf"\bweighs?\s+({_FINAL_NUMBER_V71})\s*{unit_pattern}\b",
        rf"(?is)\bper\s+(?:package|box|carton|crate|pallet|bag|drum|"
        rf"bottle|barrel|bundle|sack|case|unit|piece)\b"
        rf"[^.!?\r\n]{{0,120}}?({_FINAL_NUMBER_V71})\s*{unit_pattern}\b",
    )

    for pattern in per_package_patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        unit_value = _final_number_v71(match.group(1))
        display_unit, kg_factor = _final_weight_unit_v71(match.group(2))

        if unit_value is None or display_unit is None:
            continue

        return {
            "unit_weight": _final_round_v71(unit_value),
            "total_weight": _final_round_v71(unit_value * quantity),
            "display_unit": display_unit,
            "source_unit": str(match.group(2)).strip(),
            "package_count": _final_round_v71(quantity),
            "kg_factor": kg_factor,
            "source": "original_request_per_package",
        }

    total_patterns = (
        rf"(?is)\btotal(?:\s+shipment)?\s+weight\s*(?:is|:)?\s*"
        rf"({_FINAL_NUMBER_V71})\s*{unit_pattern}\b",
        rf"(?is)\bweighing\s+({_FINAL_NUMBER_V71})\s*{unit_pattern}"
        rf"\s+total\b",
    )

    for pattern in total_patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        total_value = _final_number_v71(match.group(1))
        display_unit, kg_factor = _final_weight_unit_v71(match.group(2))

        if total_value is None or display_unit is None:
            continue

        return {
            "unit_weight": None,
            "total_weight": _final_round_v71(total_value),
            "display_unit": display_unit,
            "source_unit": str(match.group(2)).strip(),
            "package_count": _final_round_v71(quantity),
            "kg_factor": kg_factor,
            "source": "original_request_total",
        }

    return None


def _final_volume_unit_v71(raw_unit):
    key = re.sub(r"[^a-z0-9³]+", "", str(raw_unit or "").lower())

    mapping = {
        "l": ("L", 0.001),
        "litre": ("L", 0.001),
        "litres": ("L", 0.001),
        "liter": ("L", 0.001),
        "liters": ("L", 0.001),
        "ml": ("mL", 0.000001),
        "millilitre": ("mL", 0.000001),
        "millilitres": ("mL", 0.000001),
        "milliliter": ("mL", 0.000001),
        "milliliters": ("mL", 0.000001),
        "cbm": ("m³", 1.0),
        "m3": ("m³", 1.0),
        "m³": ("m³", 1.0),
        "cubicmetre": ("m³", 1.0),
        "cubicmetres": ("m³", 1.0),
        "cubicmeter": ("m³", 1.0),
        "cubicmeters": ("m³", 1.0),
        "ft3": ("ft³", 0.028316846592),
        "ft³": ("ft³", 0.028316846592),
        "cubicfoot": ("ft³", 0.028316846592),
        "cubicfeet": ("ft³", 0.028316846592),
        "in3": ("in³", 0.000016387064),
        "in³": ("in³", 0.000016387064),
        "cubicinch": ("in³", 0.000016387064),
        "cubicinches": ("in³", 0.000016387064),
    }

    return mapping.get(key, (None, None))


# READ ORIGINAL VOLUME UNIT
# Reads the original request and extracts the display volume unit.
# Example: 10 packages at 100 litres becomes 1000 L for display.

def _final_volume_v71(text):
    quantity = _final_quantity_v71(text)
    unit_pattern = (
        r"(litres?|liters?|millilitres?|milliliters?|ml|"
        r"cbm|m3|m³|cubic\s+met(?:re|er)s?|"
        r"cubic\s+feet|cubic\s+foot|ft3|ft³|"
        r"cubic\s+inches?|in3|in³)"
    )

    patterns = (
        rf"(?is)\boriginal\s+package\s+volume\s*(?:is|:)?\s*"
        rf"({_FINAL_NUMBER_V71})\s*{unit_pattern}\b",
        rf"(?is)\beach\b.{{0,220}}?"
        rf"\b(?:has|with)\s+(?:a\s+)?(?:packed\s+)?volume\s+(?:of\s+)?"
        rf"({_FINAL_NUMBER_V71})\s*{unit_pattern}\b",
    )

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        unit_value = _final_number_v71(match.group(1))
        display_unit, cbm_factor = _final_volume_unit_v71(match.group(2))

        if unit_value is None or display_unit is None:
            continue

        return {
            "unit_volume": _final_round_v71(unit_value),
            "total_volume": _final_round_v71(unit_value * quantity),
            "display_unit": display_unit,
            "source_unit": str(match.group(2)).strip(),
            "package_count": _final_round_v71(quantity),
            "cbm_factor": cbm_factor,
            "source": "original_request_per_package",
        }

    return None


# SYNC DISPLAY AND INTERNAL WEIGHT
# Writes the user-facing weight into the final response.
# Kilograms stay internal and are repaired only when missing.

def _final_sync_weight_v71(payload, weight):
    """Synchronise the original display unit and repair a missing canonical kg
    total when the deterministic backend did not recognise the source spelling
    (for example the historical typo ``llbs``).

    Existing canonical kilogram values always win. Conversion is used only when
    ``total_weight_kg`` is absent, null, or non-numeric.
    """
    if not isinstance(payload, dict) or not isinstance(weight, dict):
        return

    display = payload.get("display_measurements")
    if not isinstance(display, dict):
        display = {}
        payload["display_measurements"] = display
    display["weight"] = dict(weight)

    metrics = payload.get("logistics_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
        payload["logistics_metrics"] = metrics

    existing_total_kg = _final_number_v71(metrics.get("total_weight_kg"))
    display_total = _final_number_v71(weight.get("total_weight"))
    kg_factor = _final_number_v71(weight.get("kg_factor"))

    repaired_total_kg = existing_total_kg
    if (
        repaired_total_kg is None
        and display_total is not None
        and kg_factor is not None
    ):
        repaired_total_kg = _final_round_v71(display_total * kg_factor)

    metrics.update(
        {
            "display_unit_weight": weight.get("unit_weight"),
            "display_total_weight": weight.get("total_weight"),
            "display_weight_unit": weight.get("display_unit"),
        }
    )

    if repaired_total_kg is not None:
        metrics["total_weight_kg"] = repaired_total_kg
        metrics["weight_known"] = True

    measurement = payload.get("cargo_measurement_status")
    if isinstance(measurement, dict) and repaired_total_kg is not None:
        measurement["weight_known"] = True

    for section_name in (
        "handoff_payload",
        "logistics_quality_review",
    ):
        section = payload.get(section_name)
        if not isinstance(section, dict):
            continue

        section.update(
            {
                "display_unit_weight": weight.get("unit_weight"),
                "display_total_weight": weight.get("total_weight"),
                "display_weight_unit": weight.get("display_unit"),
            }
        )

        if (
            repaired_total_kg is not None
            and _final_number_v71(section.get("total_weight_kg")) is None
        ):
            section["total_weight_kg"] = repaired_total_kg
            section["weight_known"] = True

    executive = payload.get("executive_summary")
    if (
        isinstance(executive, dict)
        and isinstance(executive.get("shipment_snapshot"), dict)
    ):
        snapshot = executive["shipment_snapshot"]
        snapshot.update(
            {
                "display_total_weight": weight.get("total_weight"),
                "display_weight_unit": weight.get("display_unit"),
            }
        )
        if (
            repaired_total_kg is not None
            and _final_number_v71(snapshot.get("total_weight_kg")) is None
        ):
            snapshot["total_weight_kg"] = repaired_total_kg

    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict):
        container = visualizer.get("container")
        if isinstance(container, dict):
            container.update(
                {
                    "display_total_weight": weight.get("total_weight"),
                    "display_weight_unit": weight.get("display_unit"),
                }
            )
            if (
                repaired_total_kg is not None
                and _final_number_v71(container.get("total_weight_kg")) is None
            ):
                container["total_weight_kg"] = repaired_total_kg
                container["weight_known"] = True

        cargo = visualizer.get("cargo_mix")
        if (
            isinstance(cargo, list)
            and len(cargo) == 1
            and isinstance(cargo[0], dict)
        ):
            item = cargo[0]
            item.update(
                {
                    "display_unit_weight": weight.get("unit_weight"),
                    "display_total_weight": weight.get("total_weight"),
                    "display_weight_unit": weight.get("display_unit"),
                }
            )
            if (
                repaired_total_kg is not None
                and _final_number_v71(item.get("total_weight_kg")) is None
            ):
                item["total_weight_kg"] = repaired_total_kg

            quantity = _final_number_v71(weight.get("package_count"))
            if (
                repaired_total_kg is not None
                and quantity is not None
                and quantity > 0
                and _final_number_v71(item.get("unit_weight_kg")) is None
            ):
                item["unit_weight_kg"] = _final_round_v71(
                    repaired_total_kg / quantity
                )

    metadata = payload.get("request_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        payload["request_metadata"] = metadata

    authority = metadata.get("final_display_unit_authority_v71")
    if not isinstance(authority, dict):
        authority = {"status": "applied"}
        metadata["final_display_unit_authority_v71"] = authority

    authority["weight_unit"] = weight.get("display_unit")
    authority["canonical_weight_repaired"] = (
        existing_total_kg is None and repaired_total_kg is not None
    )


# SYNC DISPLAY AND INTERNAL VOLUME
# Writes the user-facing volume into the final response.
# CBM remains the internal unit used for container planning.

def _final_sync_volume_v71(payload, volume):
    if not isinstance(volume, dict):
        return

    display = payload.get("display_measurements")
    if not isinstance(display, dict):
        display = {}
        payload["display_measurements"] = display
    display["volume"] = dict(volume)

    metrics = payload.get("logistics_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
        payload["logistics_metrics"] = metrics

    metrics.update(
        {
            "display_unit_volume": volume.get("unit_volume"),
            "display_total_volume": volume.get("total_volume"),
            "display_volume_unit": volume.get("display_unit"),
        }
    )

    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict):
        container = visualizer.get("container")
        if isinstance(container, dict):
            container.update(
                {
                    "display_total_volume": volume.get("total_volume"),
                    "display_volume_unit": volume.get("display_unit"),
                }
            )

        cargo = visualizer.get("cargo_mix")
        if (
            isinstance(cargo, list)
            and len(cargo) == 1
            and isinstance(cargo[0], dict)
        ):
            cargo[0].update(
                {
                    "display_unit_volume": volume.get("unit_volume"),
                    "display_total_volume": volume.get("total_volume"),
                    "display_volume_unit": volume.get("display_unit"),
                }
            )


# FINAL FRONTEND CLEANUP
# Normalises the final backend payload before it reaches the UI.
# It removes stale values and applies the display-unit authority.

def cleanup_frontend_response(*args, **kwargs):
    cleaned = _final_display_unit_previous_cleanup_v71(*args, **kwargs)

    if not isinstance(cleaned, dict):
        return cleaned

    original_text = _final_original_text_v71(cleaned, args, kwargs)
    weight = _final_weight_v71(original_text)
    volume = _final_volume_v71(original_text)

    _final_sync_weight_v71(cleaned, weight)
    _final_sync_volume_v71(cleaned, volume)

    metadata = cleaned.get("request_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        cleaned["request_metadata"] = metadata

    metadata["final_display_unit_authority_v71"] = {
        "status": "applied",
        "original_text_available": bool(original_text),
        "weight_unit": weight.get("display_unit") if weight else None,
        "volume_unit": volume.get("display_unit") if volume else None,
    }

    return cleaned
# END FINAL_DISPLAY_UNIT_AUTHORITY_V71


# NONPOSITIVE QUANTITY WEIGHT GUARD V77
# A zero or negative cargo quantity invalidates shipment totals.
# This final guard prevents later display-unit cleanup from restoring
# a per-package weight as though one package had been requested.
_NONPOSITIVE_QUANTITY_WEIGHT_GUARD_V77_PREVIOUS = cleanup_frontend_response


def _v77_number(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _v77_authoritative_nonpositive_quantity(payload):
    if not isinstance(payload, dict):
        return None

    validation = payload.get("input_validation_v44")
    if not isinstance(validation, dict):
        return None

    facts = validation.get("authoritative_facts")
    if not isinstance(facts, dict):
        return None

    quantity = _v77_number(facts.get("quantity"))
    if quantity is None or quantity > 0:
        return None

    errors = validation.get("errors")
    if not isinstance(errors, list):
        return None

    error_text = " ".join(str(error) for error in errors).lower()
    if "quantity must be greater than zero" not in error_text:
        return None

    return quantity


def _v77_clear_invalid_shipment_weight_fields(value):
    if isinstance(value, dict):
        for key in list(value):
            if key in {
                "total_weight_kg",
                "display_total_weight",
                "display_unit_weight",
            }:
                value[key] = None
                continue

            if key == "weight_known":
                value[key] = False
                continue

            _v77_clear_invalid_shipment_weight_fields(value[key])

    elif isinstance(value, list):
        for item in value:
            _v77_clear_invalid_shipment_weight_fields(item)


def _v77_apply_nonpositive_quantity_guard(payload):
    quantity = _v77_authoritative_nonpositive_quantity(payload)
    if quantity is None:
        return payload

    _v77_clear_invalid_shipment_weight_fields(payload)

    display = payload.get("display_measurements")
    if isinstance(display, dict):
        weight = display.get("weight")
        if isinstance(weight, dict):
            weight["package_count"] = (
                int(quantity) if quantity.is_integer() else quantity
            )
            weight["total_weight"] = None

    metadata = payload.setdefault("request_metadata", {})
    if isinstance(metadata, dict):
        metadata["nonpositive_quantity_weight_guard_v77"] = {
            "status": "applied",
            "authoritative_quantity": (
                int(quantity) if quantity.is_integer() else quantity
            ),
            "shipment_weight_totals_cleared": True,
        }

    return payload


def cleanup_frontend_response(payload, original_text=None):
    payload = _NONPOSITIVE_QUANTITY_WEIGHT_GUARD_V77_PREVIOUS(
        payload,
        original_text,
    )
    return _v77_apply_nonpositive_quantity_guard(payload)
