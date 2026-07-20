from __future__ import annotations

import re
from typing import Any


def _clean_text(text: str | None) -> str:
    if not text:
        return ""

    cleaned = " ".join(str(text).split())

    replacements = {
        "kg.Recommended": "kg. Recommended",
        "kg.Recommended container": "kg. Recommended container",
        "supplieroption": "supplier option",
        "Risk,Compliance": "Risk, Compliance",
        "andFinance": "and Finance",
        "catalog item'": "catalog item '",
        "catalogitem": "catalog item",
        "item'": "item '",
    }

    for old_value, new_value in replacements.items():
        cleaned = cleaned.replace(old_value, new_value)

    cleaned = re.sub(r"(\d+(?:\.\d+)?)kg\b", r"\1 kg", cleaned)
    cleaned = cleaned.replace("kg.Recommended", "kg. Recommended")
    cleaned = cleaned.replace("kg. Recommended container", "kg. Recommended container")

    return cleaned.strip()


def _shorten(text: str | None, limit: int = 500) -> str:
    cleaned = _clean_text(text)

    if len(cleaned) <= limit:
        return cleaned

    return cleaned[:limit].rstrip() + "..."


def _is_assumption_or_estimate(message: str) -> bool:
    lowered = message.lower()

    return any(
        marker in lowered
        for marker in [
            "estimated from catalog",
            "matched from catalog",
            "direct cbm was provided",
        ]
    )


def _build_short_answer(
    response: dict[str, Any],
    final_verdict: dict[str, Any],
    logistics_metrics: dict[str, Any],
    partner_review: dict[str, Any],
) -> str:
    decision = final_verdict.get("verdict", response.get("status"))
    agents_called = ", ".join(response.get("agents_called", []))

    parts = [
        f"Decision: {decision}.",
        f"Agents called: {agents_called}.",
    ]

    if logistics_metrics:
        parts.append(
            "Logistics: "
            f"{logistics_metrics.get('total_cbm')} CBM, "
            f"{logistics_metrics.get('total_weight_kg')} kg, "
            f"recommended container {logistics_metrics.get('recommended_container')}, "
            f"risk level {logistics_metrics.get('risk_level')}."
        )

    if partner_review:
        parts.append(
            "Partner review: "
            f"{partner_review.get('status')}."
        )

    return _clean_text(" ".join(parts))


def _split_missing_information(missing_information: list[Any]) -> tuple[list[str], list[str]]:
    real_missing = []
    assumptions = []

    for item in missing_information:
        cleaned_item = _clean_text(str(item))

        if _is_assumption_or_estimate(cleaned_item):
            assumptions.append(cleaned_item)
        else:
            real_missing.append(cleaned_item)

    return real_missing, assumptions


def _frontend_final_verdict(
    final_verdict: dict[str, Any],
    real_missing: list[str],
    assumptions: list[str],
) -> dict[str, Any]:
    frontend_verdict = dict(final_verdict)
    frontend_verdict["missing_information_count"] = len(real_missing)
    frontend_verdict["assumptions_count"] = len(assumptions)
    return frontend_verdict




def _extract_logistics_metrics(response: dict[str, Any]) -> dict[str, Any]:
    logistics_response = response.get("specialist_responses", {}).get("logistics_agent", {})

    if not isinstance(logistics_response, dict):
        return {}

    handoff_payload = logistics_response.get("handoff_payload", {})

    return {
        "total_cbm": handoff_payload.get("total_cbm"),
        "total_weight_kg": handoff_payload.get("total_weight_kg"),
        "recommended_container": handoff_payload.get("recommended_container"),
        "recommended_load_type": handoff_payload.get("recommended_load_type"),
        "risk_level": handoff_payload.get("risk_level"),
        "risk_score": handoff_payload.get("risk_score"),
        "readiness_status": handoff_payload.get("readiness_status"),
    }



def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _round_number(value: Any, digits: int = 2) -> Any:
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def _cargo_category_tags(item: dict[str, Any]) -> list[str]:
    tags = item.get("cargo_categories")

    if isinstance(tags, list):
        return sorted({str(tag) for tag in tags if tag})

    inferred_tags = []

    for field_name, tag_name in [
        ("fragile", "fragile"),
        ("perishable", "perishable"),
        ("hazardous", "hazardous"),
        ("radioactive", "radioactive"),
    ]:
        if item.get(field_name):
            inferred_tags.append(tag_name)

    if item.get("stackable") is False:
        inferred_tags.append("non_stackable")

    if isinstance(item.get("weight_kg"), (int, float)) and item["weight_kg"] >= 50:
        inferred_tags.append("heavy")

    return sorted(set(inferred_tags))


def _extract_logistics_visualizer(response: dict[str, Any]) -> dict[str, Any]:
    logistics_response = _safe_dict(
        response.get("specialist_responses", {}).get("logistics_agent")
    )

    plan = _safe_dict(logistics_response.get("plan"))
    handoff_payload = _safe_dict(logistics_response.get("handoff_payload"))
    logistics_metrics = _extract_logistics_metrics(response)

    if not plan and not handoff_payload and not logistics_metrics:
        return {}

    item_breakdown = _safe_list(plan.get("item_breakdown"))
    container_recommendation = _safe_dict(plan.get("container_recommendation"))
    container_fit = _safe_dict(plan.get("container_fit"))
    container_layout = _safe_dict(plan.get("container_layout"))
    loading_sequence = _safe_list(plan.get("loading_sequence"))

    container_options = _safe_list(plan.get("container_options"))
    if not container_options:
        container_options = _safe_list(handoff_payload.get("container_options"))

    selected_container = (
        container_recommendation.get("container_name")
        or handoff_payload.get("recommended_container")
        or logistics_metrics.get("recommended_container")
        or container_layout.get("container")
    )

    selected_option = {}

    for option in container_options:
        if not isinstance(option, dict):
            continue

        if option.get("option_name") == selected_container:
            selected_option = option
            break

    cargo_mix = []

    for item in item_breakdown:
        if not isinstance(item, dict):
            continue

        cargo_mix.append(
            {
                "item_name": item.get("name") or item.get("item_name"),
                "quantity": item.get("quantity"),
                "dimensions_m": {
                    "length": item.get("length_m"),
                    "width": item.get("width_m"),
                    "height": item.get("height_m"),
                },
                "unit_cbm": _round_number(item.get("unit_cbm")),
                "total_cbm": _round_number(item.get("total_cbm")),
                "unit_weight_kg": _round_number(item.get("weight_kg")),
                "total_weight_kg": _round_number(item.get("total_weight_kg")),
                "stackable": item.get("stackable"),
                "unload_priority": item.get("unload_priority"),
                "category_tags": _cargo_category_tags(item),
            }
        )

    visual_loading_sequence = []

    for item in loading_sequence:
        if not isinstance(item, dict):
            continue

        visual_loading_sequence.append(
            {
                "sequence_number": item.get("sequence_number") or item.get("loading_stage"),
                "item_name": item.get("item_name"),
                "quantity": item.get("quantity"),
                "suggested_zone": _clean_text(item.get("suggested_zone")),
                "category_tags": _safe_list(item.get("categories")),
                "reason": _clean_text(item.get("reason")),
            }
        )

    visual_container_options = []

    for option in container_options[:6]:
        if not isinstance(option, dict):
            continue

        visual_container_options.append(
            {
                "option_name": option.get("option_name"),
                "container_count": option.get("container_count"),
                "total_capacity_cbm": _round_number(option.get("total_capacity_cbm")),
                "safe_capacity_cbm": _round_number(option.get("total_safe_cbm")),
                "payload_limit_kg": _round_number(option.get("total_payload_kg")),
                "estimated_utilization_percent": _round_number(
                    option.get("estimated_utilization_percent")
                ),
                "unused_safe_cbm": _round_number(option.get("unused_safe_cbm")),
                "reason": _clean_text(option.get("reason")),
            }
        )

    fit_warnings = [
        _clean_text(warning)
        for warning in _safe_list(container_fit.get("warnings"))
        if _clean_text(warning)
    ]

    fit_recommendations = [
        _clean_text(recommendation)
        for recommendation in _safe_list(container_fit.get("recommendations"))
        if _clean_text(recommendation)
    ]

    layout_notes = [
        _clean_text(note)
        for note in _safe_list(container_layout.get("layout_notes"))
        if _clean_text(note)
    ]

    zone_layout = []

    for zone in _safe_list(container_layout.get("zones")):
        if not isinstance(zone, dict):
            continue

        zone_items = []

        for zone_item in _safe_list(zone.get("items")):
            if not isinstance(zone_item, dict):
                continue

            zone_items.append(
                {
                    "item_name": zone_item.get("item_name"),
                    "quantity": zone_item.get("quantity"),
                    "sequence_number": zone_item.get("sequence_number"),
                    "reason": _clean_text(zone_item.get("reason")),
                }
            )

        zone_layout.append(
            {
                "zone_name": zone.get("zone_name"),
                "description": _clean_text(zone.get("description")),
                "items": zone_items,
            }
        )

    utilization_percent = (
        container_recommendation.get("estimated_utilization_percent")
        or handoff_payload.get("container_utilization_percent")
        or selected_option.get("estimated_utilization_percent")
    )

    return {
        "visualizer_type": "container_load_visualizer",
        "status": "available",
        "container": {
            "selected_container": selected_container,
            "recommended_load_type": handoff_payload.get("recommended_load_type")
            or logistics_metrics.get("recommended_load_type"),
            "total_cbm": _round_number(
                handoff_payload.get("total_cbm") or logistics_metrics.get("total_cbm")
            ),
            "total_weight_kg": _round_number(
                handoff_payload.get("total_weight_kg")
                or logistics_metrics.get("total_weight_kg")
            ),
            "total_items": handoff_payload.get("total_items"),
            "capacity_cbm": _round_number(
                container_recommendation.get("capacity_cbm")
                or selected_option.get("total_capacity_cbm")
            ),
            "safe_capacity_cbm": _round_number(
                container_recommendation.get("safe_cbm_limit")
                or selected_option.get("total_safe_cbm")
            ),
            "max_payload_kg": _round_number(
                container_recommendation.get("max_payload_kg")
                or selected_option.get("total_payload_kg")
            ),
            "utilization_percent": _round_number(utilization_percent),
            "risk_level": logistics_metrics.get("risk_level"),
            "risk_score": logistics_metrics.get("risk_score"),
        },
        "cargo_mix": cargo_mix,
        "container_options": visual_container_options,
        "zone_layout": zone_layout,
        "loading_sequence": visual_loading_sequence,
        "fit_check": {
            "status": container_fit.get("fit_status"),
            "selected_container_checked": container_fit.get("selected_container_checked"),
            "warnings": fit_warnings,
            "recommendations": fit_recommendations,
            "item_fit_results": _safe_list(container_fit.get("item_fit_results")),
        },
        "layout_notes": layout_notes,
        "frontend_hints": {
            "primary_view": "container_utilization",
            "secondary_view": "zone_layout",
            "show_cargo_tags": True,
            "show_fit_warnings": bool(fit_warnings),
            "show_loading_sequence": bool(visual_loading_sequence),
        },
    }

def _extract_agent_summaries(response: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = []
    specialist_responses = response.get("specialist_responses", {})

    for agent_name, agent_response in specialist_responses.items():
        if not isinstance(agent_response, dict):
            continue

        summaries.append(
            {
                "agent_name": agent_name,
                "status": agent_response.get("status"),
                "summary": _clean_text(agent_response.get("summary")),
            }
        )

    return summaries


def build_frontend_payload(response: dict[str, Any], include_raw_response: bool = False) -> dict[str, Any]:
    final_verdict = response.get("final_verdict", {})
    partner_review = response.get("partner_review", {})
    missing_information = response.get("missing_information", [])
    real_missing, assumptions = _split_missing_information(missing_information)

    payload = {
        "agent_name": response.get("agent_name"),
        "status": response.get("status"),
        "detected_intent": response.get("detected_intent"),
        "agents_called": response.get("agents_called", []),
        "summary": response.get("summary"),
        "short_answer": _build_short_answer(
            response=response,
            final_verdict=final_verdict,
            logistics_metrics=_extract_logistics_metrics(response),
            partner_review=partner_review,
        ),
        "final_verdict": _frontend_final_verdict(
            final_verdict=final_verdict,
            real_missing=real_missing,
            assumptions=assumptions,
        ),
        "decision": final_verdict.get("verdict"),
        "logistics_metrics": _extract_logistics_metrics(response),
        "logistics_visualizer": _extract_logistics_visualizer(response),
        "partner_review_status": partner_review.get("status"),
        "partner_review_summary": partner_review.get("summary"),
        "missing_information_count": len(real_missing),
        "missing_information_preview": real_missing[:5],
        "assumptions_count": len(assumptions),
        "assumptions_preview": assumptions[:5],
        "agent_summaries": _extract_agent_summaries(response),
    }

    if include_raw_response:
        payload["raw_response"] = response

    return payload
