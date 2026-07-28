from __future__ import annotations

import re
from typing import Any

STANDARD_LENGTH_M = 5.90
STANDARD_WIDTH_M = 2.35
STANDARD_HEIGHT_M = 2.39
STANDARD_CAPACITY_CBM = 33.20
STANDARD_SAFE_CAPACITY_CBM = 28.22
STANDARD_PAYLOAD_KG = 28200.0


def _is_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _rounded(value: float) -> int | float:
    rounded = round(float(value), 6)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def _prompt_text(payload: dict[str, Any], prompt_text: str | None) -> str:
    direct = str(prompt_text or "").strip()
    if direct:
        return direct
    metadata = payload.get("request_metadata")
    if _is_dict(metadata):
        return str(metadata.get("input_source") or "").strip()
    return ""


def _direct_multi_items(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?P<cbm>[0-9][0-9,]*(?:\.[0-9]+)?)\s*CBM\s+"
        r"(?:of\s+)?"
        r"(?P<name>.*?)"
        r"\s+weigh(?:ing|s)?\s+"
        r"(?P<weight>[0-9][0-9,]*(?:\.[0-9]+)?)\s*kg\b",
        flags=re.IGNORECASE,
    )

    items: list[dict[str, Any]] = []

    for match in pattern.finditer(text):
        cbm = float(match.group("cbm").replace(",", ""))
        name = re.sub(
            r"\s+",
            " ",
            match.group("name"),
        ).strip(" ,.:;-")
        weight = float(match.group("weight").replace(",", ""))

        if not name or cbm <= 0 or weight <= 0:
            continue

        items.append(
            {
                "item_name": name.lower(),
                "quantity": 1,
                "total_cbm": _rounded(cbm),
                "unit_cbm": _rounded(cbm),
                "total_weight_kg": _rounded(weight),
                "unit_weight_kg": _rounded(weight),
                "aggregate_volume_only": True,
                "dimensions_are_aggregate": True,
                "display_dimensions_estimated": True,
                "weight_estimated": False,
                "weight_source": "explicit_user_item_weight",
                "category_tags": ["general_cargo"],
            }
        )

    return items if len(items) >= 2 else []

def _route(text: str) -> tuple[str | None, str | None]:
    origin = None
    destination = None

    route_match = re.search(
        r"\bfrom\s+([A-Za-z][A-Za-z .'-]{1,40}?)\s+to\s+"
        r"([A-Za-z][A-Za-z .'-]{1,40}?)(?=[.,;]|\s+(?:using|under|with)\b|$)",
        text,
        flags=re.IGNORECASE,
    )
    if route_match:
        origin = route_match.group(1).strip(" ,.")
        destination = route_match.group(2).strip(" ,.")

    return origin, destination


def _oversized_item(text: str) -> dict[str, Any] | None:
    dimensions = re.search(
        r"\b(?:packed\s+)?dimensions?\s*(?:are|is|=|:)?\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s*[x×]\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s*[x×]\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\b",
        text,
        flags=re.IGNORECASE,
    )
    weight_match = re.search(
        r"\b(?:it\s+)?weighs?\s*([0-9]+(?:\.[0-9]+)?)\s*kg\b",
        text,
        flags=re.IGNORECASE,
    )
    if not dimensions or not weight_match:
        return None

    length = float(dimensions.group(1))
    width = float(dimensions.group(2))
    height = float(dimensions.group(3))
    weight = float(weight_match.group(1))

    if not (
        length > STANDARD_LENGTH_M
        or width > STANDARD_WIDTH_M
        or height > STANDARD_HEIGHT_M
    ):
        return None

    name_match = re.search(
        r"\bship\s+(?:(?:one|1|a|an)\s+)?(.+?)\s+from\b",
        text,
        flags=re.IGNORECASE,
    )
    name = "oversized cargo"
    if name_match:
        candidate = re.sub(r"\s+", " ", name_match.group(1)).strip(" ,.:;-")
        candidate = re.sub(r"^(?:one|1|a|an)\s+", "", candidate, flags=re.IGNORECASE)
        if candidate:
            name = candidate.lower()

    cbm = length * width * height
    non_stackable = bool(re.search(r"\bnon[-\s]?stackable\b", text, flags=re.IGNORECASE))

    return {
        "item_name": name,
        "quantity": 1,
        "dimensions_m": {
            "length": _rounded(length),
            "width": _rounded(width),
            "height": _rounded(height),
        },
        "length_m": _rounded(length),
        "width_m": _rounded(width),
        "height_m": _rounded(height),
        "unit_cbm": _rounded(cbm),
        "total_cbm": _rounded(cbm),
        "unit_weight_kg": _rounded(weight),
        "total_weight_kg": _rounded(weight),
        "stackable": not non_stackable,
        "weight_estimated": False,
        "weight_source": "explicit_user_item_weight",
        "category_tags": ["oversized", "heavy"] + (["non_stackable"] if non_stackable else []),
    }


def _remove_known_questions(payload: dict[str, Any]) -> None:
    def keep(value: Any) -> bool:
        text = str(value or "").lower()
        asks_dimensions = "dimension" in text or "packed size" in text or "cbm" in text
        asks_weight = "weight" in text or "weigh" in text
        return not (asks_dimensions or asks_weight)

    for key in ("clarification_questions", "missing_information", "questions"):
        values = payload.get(key)
        if isinstance(values, list):
            payload[key] = [value for value in values if keep(value)]

    action_plan = payload.get("action_plan")
    if _is_dict(action_plan):
        for key in ("user_questions", "questions", "missing_information"):
            values = action_plan.get(key)
            if isinstance(values, list):
                action_plan[key] = [value for value in values if keep(value)]


def _remove_standard_quote_advice(payload: dict[str, Any]) -> None:
    def clean(values: Any) -> Any:
        if not isinstance(values, list):
            return values
        output = []
        for value in values:
            lower = str(value or "").lower()
            if "compare fcl quotes" in lower:
                continue
            if "20ft, 40ft" in lower or "20ft, 40ft, and 40ft" in lower:
                continue
            output.append(value)
        return output

    for key in ("recommended_actions", "recommendations", "next_steps"):
        if key in payload:
            payload[key] = clean(payload.get(key))

    action_plan = payload.get("action_plan")
    if _is_dict(action_plan):
        for key in ("recommended_actions", "recommendations", "next_steps"):
            if key in action_plan:
                action_plan[key] = clean(action_plan.get(key))


def _sync_multi_item(payload: dict[str, Any], items: list[dict[str, Any]], text: str) -> None:
    total_cbm = sum(float(item["total_cbm"]) for item in items)
    total_weight = sum(float(item["total_weight_kg"]) for item in items)
    utilization = round((total_cbm / STANDARD_CAPACITY_CBM) * 100, 2)

    metrics = payload.setdefault("logistics_metrics", {})
    if not _is_dict(metrics):
        metrics = {}
        payload["logistics_metrics"] = metrics
    metrics.update(
        {
            "total_cbm": _rounded(total_cbm),
            "total_weight_kg": _rounded(total_weight),
            "recommended_container": "20ft Standard Container",
            "recommended_load_type": "fcl_preferred",
            "readiness_status": "ready_for_standard_review",
        }
    )

    visualizer = payload.setdefault("logistics_visualizer", {})
    if not _is_dict(visualizer):
        visualizer = {}
        payload["logistics_visualizer"] = visualizer
    visualizer["status"] = "available"
    visualizer["visualizer_type"] = "container_load_visualizer"
    visualizer["cargo_mix"] = items

    container = visualizer.setdefault("container", {})
    if not _is_dict(container):
        container = {}
        visualizer["container"] = container
    container.update(
        {
            "selected_container": "20ft Standard Container",
            "recommended_load_type": "fcl_preferred",
            "total_cbm": _rounded(total_cbm),
            "total_weight_kg": _rounded(total_weight),
            "total_items": len(items),
            "capacity_cbm": STANDARD_CAPACITY_CBM,
            "safe_capacity_cbm": STANDARD_SAFE_CAPACITY_CBM,
            "max_payload_kg": int(STANDARD_PAYLOAD_KG),
            "utilization_percent": utilization,
        }
    )

    visualizer["display_metrics"] = {
        "loaded_cbm": _rounded(total_cbm),
        "container_cbm": STANDARD_CAPACITY_CBM,
        "remaining_cbm": _rounded(max(0.0, STANDARD_CAPACITY_CBM - total_cbm)),
        "utilization_percent": utilization,
        "basis": "shipment_total_cbm",
    }
    visualizer["fit_check"] = {
        "status": "fits_selected_container",
        "selected_container_checked": "20ft Standard Container",
        "warnings": [],
        "recommendations": [
            "Confirm supplier packing details and weight distribution before booking."
        ],
    }
    visualizer["loading_sequence"] = [
        {
            "sequence_number": index,
            "item_name": item["item_name"],
            "quantity": item["quantity"],
            "suggested_zone": "floor_loaded_balanced_zone",
            "reason": "Place heavier or denser cargo first and maintain balanced weight distribution.",
        }
        for index, item in enumerate(items, start=1)
    ]

    handoff = payload.setdefault("handoff_payload", {})
    if _is_dict(handoff):
        handoff["total_cbm"] = _rounded(total_cbm)
        handoff["total_weight_kg"] = _rounded(total_weight)
        handoff["recommended_container"] = "20ft Standard Container"

    review = payload.setdefault("logistics_quality_review", {})
    if _is_dict(review):
        review["total_cbm"] = _rounded(total_cbm)
        review["total_weight_kg"] = _rounded(total_weight)

    _remove_known_questions(payload)


def _sync_oversized(payload: dict[str, Any], item: dict[str, Any], text: str) -> None:
    cbm = float(item["total_cbm"])
    weight = float(item["total_weight_kg"])
    utilization = round((cbm / STANDARD_CAPACITY_CBM) * 100, 2)
    name = str(item["item_name"])
    dimensions = item["dimensions_m"]
    recommendation = "Special equipment required: flat rack, open-top, or breakbulk review"

    payload["status"] = "critical_review_required"
    payload["decision"] = "critical_review_required"
    payload["detected_intent"] = "logistics"

    metrics = payload.setdefault("logistics_metrics", {})
    if not _is_dict(metrics):
        metrics = {}
        payload["logistics_metrics"] = metrics
    metrics.update(
        {
            "total_cbm": _rounded(cbm),
            "total_weight_kg": _rounded(weight),
            "recommended_container": recommendation,
            "recommended_load_type": "specialist_oversized_cargo",
            "risk_level": "high",
            "risk_score": 8,
            "readiness_status": "not_ready_oversized_dimensions",
        }
    )

    visualizer = payload.setdefault("logistics_visualizer", {})
    if not _is_dict(visualizer):
        visualizer = {}
        payload["logistics_visualizer"] = visualizer
    visualizer.update(
        {
            "status": "available",
            "visualizer_type": "container_load_visualizer",
            "cargo_mix": [item],
            "loading_sequence": [
                {
                    "sequence_number": 1,
                    "item_name": name,
                    "quantity": 1,
                    "suggested_zone": "specialist_equipment_reference",
                    "reason": "The cargo exceeds standard closed-container dimensions and requires an out-of-gauge loading plan.",
                }
            ],
            "zone_layout": [],
            "layout_notes": [
                "The physical item is intentionally not drawn inside the standard reference container because it does not fit.",
                "Use a flat rack, open-top, or breakbulk plan after carrier engineering review.",
            ],
        }
    )

    visualizer["container"] = {
        "selected_container": recommendation,
        "recommended_load_type": "specialist_oversized_cargo",
        "total_cbm": _rounded(cbm),
        "total_weight_kg": _rounded(weight),
        "total_items": 1,
        "capacity_cbm": STANDARD_CAPACITY_CBM,
        "safe_capacity_cbm": STANDARD_SAFE_CAPACITY_CBM,
        "max_payload_kg": int(STANDARD_PAYLOAD_KG),
        "utilization_percent": utilization,
        "length_m": STANDARD_LENGTH_M,
        "width_m": STANDARD_WIDTH_M,
        "height_m": STANDARD_HEIGHT_M,
    }
    visualizer["display_metrics"] = {
        "loaded_cbm": _rounded(cbm),
        "container_cbm": STANDARD_CAPACITY_CBM,
        "remaining_cbm": 0,
        "utilization_percent": utilization,
        "basis": "shipment_total_cbm",
    }
    visualizer["fit_check"] = {
        "status": "does_not_fit_standard_container",
        "selected_container_checked": "20ft Standard Container",
        "warnings": [
            "Cargo dimensions exceed standard closed-container internal limits."
        ],
        "recommendations": [
            "Use flat rack, open-top, or breakbulk planning and obtain carrier out-of-gauge approval before booking."
        ],
    }
    visualizer["container_options"] = [
        {
            "option_name": "Flat rack / open-top specialist review",
            "estimated_utilization_percent": utilization,
            "safe_capacity_cbm": None,
            "payload_limit_kg": None,
        }
    ]

    origin, destination = _route(text)
    handoff = payload.setdefault("handoff_payload", {})
    if _is_dict(handoff):
        handoff.update(
            {
                "total_cbm": _rounded(cbm),
                "total_weight_kg": _rounded(weight),
                "recommended_container": recommendation,
                "risk_level": "high",
                "cargo_categories": ["oversized", "heavy"],
            }
        )
        if origin:
            handoff["origin"] = origin
        if destination:
            handoff["destination"] = destination

    payload["booking_readiness"] = {
        "score": 15,
        "ready_for_first_pass": True,
        "ready_for_booking": False,
        "next_gate": "specialist_equipment_and_carrier_review",
        "blockers": [
            "Cargo dimensions exceed a standard closed container."
        ],
    }

    review = payload.setdefault("logistics_quality_review", {})
    if _is_dict(review):
        review.update(
            {
                "status": "blocked",
                "summary": "Standard closed-container booking is blocked by the cargo dimensions.",
                "total_cbm": _rounded(cbm),
                "total_weight_kg": _rounded(weight),
                "recommended_container": recommendation,
            }
        )

    _remove_known_questions(payload)
    _remove_standard_quote_advice(payload)

    specialist_actions = [
        "Obtain a carrier or project-cargo review for flat rack, open-top, or breakbulk handling.",
        "Confirm the center of gravity, lifting points, securing method, and out-of-gauge dimensions.",
        "Obtain route and terminal clearance before booking.",
    ]
    payload["recommended_actions"] = specialist_actions

    action_plan = payload.setdefault("action_plan", {})
    if _is_dict(action_plan):
        action_plan["recommended_actions"] = specialist_actions
        action_plan["user_questions"] = []

    answer = (
        "Do not book this as a standard closed-container shipment.\n\n"
        f"The {name} is {dimensions['length']} m x {dimensions['width']} m x "
        f"{dimensions['height']} m, with a packed volume of {_rounded(cbm)} CBM and "
        f"a total weight of {_rounded(weight)} kg. "
        "Its dimensions exceed the 20ft standard reference container.\n\n"
        f"Recommended approach: {recommendation}. The item is omitted from the standard-container "
        "3D interior because drawing it there would falsely imply that it fits.\n\n"
        "Next actions: obtain specialist carrier approval, confirm center of gravity and lifting points, "
        "prepare an engineered securing plan, and verify route and terminal out-of-gauge clearance."
    )
    payload["display_answer"] = answer
    payload["frontend_answer"] = answer
    payload["short_answer"] = answer.split("\n\n", 1)[0]

    final_answer = payload.setdefault("final_answer", {})
    if _is_dict(final_answer):
        final_answer.update(
            {
                "answer_text": answer,
                "headline": "Specialist oversized-cargo planning required",
                "status": "blocked",
            }
        )

    sections = payload.get("ui_sections")
    if isinstance(sections, list):
        for section in sections:
            if not _is_dict(section):
                continue
            if section.get("section_id") == "logistics":
                section["status"] = "blocked"
                section["summary"] = (
                    "The cargo exceeds standard closed-container dimensions and requires specialist equipment planning."
                )


def apply_container_planning_consistency(
    payload: Any,
    prompt_text: str | None = None,
) -> Any:
    if not _is_dict(payload):
        return payload

    text = _prompt_text(payload, prompt_text)
    if not text:
        return payload

    direct_items = _direct_multi_items(text)
    if direct_items:
        _sync_multi_item(payload, direct_items, text)

    oversized = _oversized_item(text)
    if oversized:
        _sync_oversized(payload, oversized, text)

    return payload
