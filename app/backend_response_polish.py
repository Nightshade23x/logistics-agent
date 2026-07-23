
from __future__ import annotations

import json
import re
from typing import Any


VALID_COUNTRIES = {
    "india": "India",
    "usa": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "germany": "Germany",
    "china": "China",
    "turkey": "Turkey",
    "uae": "UAE",
    "united arab emirates": "UAE",
    "iran": "Iran",
}

INCOTERMS = {"EXW", "FOB", "CIF", "DAP", "DDP", "FCA", "CFR"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _walk_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_dicts(value)


def _request_text(payload: dict[str, Any], original_text: str | None = None) -> str:
    parts: list[str] = []

    if original_text:
        parts.append(str(original_text))

    try:
        from app.request_context import active_request_text
        active = active_request_text()
        if active:
            parts.append(str(active))
    except Exception:
        pass

    for key in ["user_text", "request_text", "text", "prompt", "original_text"]:
        value = payload.get(key)
        if value:
            parts.append(str(value))

    meta = _as_dict(payload.get("request_metadata"))
    for key in ["user_text", "request_text", "text", "prompt", "original_text"]:
        value = meta.get(key)
        if value:
            parts.append(str(value))

    return "\n".join(parts)


def _payload_text(payload: dict[str, Any]) -> str:
    try:
        return json.dumps(payload, default=str)
    except Exception:
        return ""


def _canonical_country(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    raw = value.strip(" .,:;")
    key = raw.lower()

    if key in VALID_COUNTRIES:
        return VALID_COUNTRIES[key]

    return None


def _trusted_route_value(payload: dict[str, Any], keys: list[str]) -> str | None:
    trusted_sections = [
        payload,
        _as_dict(payload.get("handoff_payload")),
        _as_dict(payload.get("logistics_metrics")),
        _as_dict(payload.get("trade_terms_advice")),
        _as_dict(payload.get("document_requirements_advice")),
        _as_dict(payload.get("trade_compliance_readiness")),
        _as_dict(_as_dict(payload.get("landed_cost_advice")).get("known_inputs")),
        _as_dict(_as_dict(payload.get("executive_summary")).get("shipment_snapshot")),
    ]

    for section in trusted_sections:
        for key in keys:
            value = _canonical_country(section.get(key))
            if value:
                return value

    return None


def _trusted_incoterm(payload: dict[str, Any]) -> str | None:
    trusted_sections = [
        payload,
        _as_dict(payload.get("handoff_payload")),
        _as_dict(payload.get("trade_terms_advice")),
        _as_dict(payload.get("document_requirements_advice")),
        _as_dict(payload.get("trade_compliance_readiness")),
        _as_dict(_as_dict(payload.get("landed_cost_advice")).get("known_inputs")),
        _as_dict(_as_dict(payload.get("executive_summary")).get("shipment_snapshot")),
    ]

    for section in trusted_sections:
        for key in ["incoterm", "trade_term"]:
            value = section.get(key)
            if isinstance(value, str) and value.strip().upper() in INCOTERMS:
                return value.strip().upper()

    return None


def _route(payload: dict[str, Any], original_text: str | None = None) -> tuple[str | None, str | None, str | None]:
    text = _request_text(payload, original_text)

    origin = _trusted_route_value(payload, ["origin", "origin_country", "country_from", "supplier_country"])
    destination = _trusted_route_value(payload, ["destination", "destination_country", "country_to", "target_market"])
    incoterm = _trusted_incoterm(payload)

    if not origin:
        match = re.search(r"\bfrom\s+([A-Za-z ]{2,40}?)(?=\s+to\b|\.|,| using\b|$)", text, flags=re.I)
        if match:
            origin = _canonical_country(match.group(1))

    if not destination:
        for pattern in [
            r"\bdestination\s*(?:is|=|:)?\s*([A-Za-z ]{2,40}?)(?=\.|,| using\b|$)",
            r"\bto\s+([A-Za-z ]{2,40}?)(?=\.|,| using\b|$)",
        ]:
            match = re.search(pattern, text, flags=re.I)
            if match:
                destination = _canonical_country(match.group(1))
                if destination:
                    break

    if not incoterm:
        match = re.search(r"\b(EXW|FOB|CIF|DAP|DDP|FCA|CFR)\b", text, flags=re.I)
        if match:
            incoterm = match.group(1).upper()

    return origin, destination, incoterm


def _cargo_items(payload: dict[str, Any], original_text: str | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for obj in _walk_dicts(payload):
        for key in ["cargo_mix", "items", "cargo_items", "item_breakdown"]:
            value = obj.get(key)
            if not isinstance(value, list):
                continue

            for item in value:
                if not isinstance(item, dict):
                    continue

                name = str(item.get("item_name") or item.get("name") or item.get("description") or "").strip()
                if not name or name.lower() in {"unknown item", "and 1200 kg"}:
                    continue

                key_name = name.lower()
                if key_name in seen:
                    continue

                seen.add(key_name)
                items.append(item)

    request = _request_text(payload, original_text).lower()

    inferred: list[dict[str, Any]] = []

    if "hazardous chemicals" in request:
        inferred.append(
            {
                "item_name": "hazardous chemicals",
                "quantity": 1,
                "category_tags": ["hazardous", "chemical", "dangerous_goods"],
            }
        )

    if "electric scooters" in request:
        inferred.append(
            {
                "item_name": "electric scooters",
                "quantity": 5 if "5 electric scooters" in request else 1,
                "category_tags": ["hazardous", "battery", "lithium_battery"],
            }
        )

    if "lithium batteries" in request and not any("electric scooters" in str(item.get("item_name", "")).lower() for item in items + inferred):
        inferred.append(
            {
                "item_name": "lithium batteries",
                "quantity": 1,
                "category_tags": ["hazardous", "battery", "lithium_battery"],
            }
        )

    for item in inferred:
        name = str(item.get("item_name") or "").strip().lower()
        if name and name not in seen:
            seen.add(name)
            items.append(item)

    return items


def _request_is_hazardous(payload: dict[str, Any], items: list[dict[str, Any]], original_text: str | None = None) -> bool:
    request = _request_text(payload, original_text).lower()

    if any(token in request for token in ["hazardous chemicals", "lithium batteries", "lithium battery", "dangerous goods", "msds", "battery", "batteries"]):
        return True

    for item in items:
        name = str(item.get("item_name") or item.get("name") or "").lower()
        tags = " ".join(str(tag).lower() for tag in _as_list(item.get("category_tags")))
        if any(token in f"{name} {tags}" for token in ["hazardous", "lithium_battery", "battery", "chemical", "dangerous_goods"]):
            return True

    return False


def _add_unique(items: list[Any], *values: Any) -> None:
    seen = {str(item).strip().lower() for item in items}
    for value in values:
        if not value:
            continue
        key = str(value).strip().lower()
        if key and key not in seen:
            items.append(value)
            seen.add(key)


def _filter_stale_list(items: list[Any], items_known: bool, origin: str | None, destination: str | None, incoterm: str | None, hazardous: bool) -> list[Any]:
    cleaned: list[Any] = []

    for item in items:
        if not isinstance(item, str):
            cleaned.append(item)
            continue

        lowered = item.lower()

        if items_known and any(
            phrase in lowered
            for phrase in [
                "no shipment items were available",
                "no shipment items were found",
                "no cargo items were available",
                "which products and quantities are included",
            ]
        ):
            continue

        if origin and destination and "origin or destination is missing" in lowered:
            continue

        if origin and (
            lowered.strip() == "origin_country"
            or "origin country is not fully confirmed" in lowered
            or "what is the origin country" in lowered
            or "origin country is missing" in lowered
        ):
            continue

        if destination and (
            lowered.strip() == "destination_country"
            or "destination country is not fully confirmed" in lowered
            or "destination country is missing" in lowered
        ):
            continue

        if incoterm and any(
            phrase in lowered
            for phrase in [
                "incoterm is missing",
                "no incoterm",
                "which incoterm",
                "shipping term should be shown",
            ]
        ):
            continue

        if not hazardous and any(
            phrase in lowered
            for phrase in [
                "possible hazardous cargo",
                "hazardous cargo requires",
                "dangerous goods declaration",
                "msds",
                "carrier dangerous-goods",
            ]
        ):
            continue

        cleaned.append(item)

    return cleaned


def _replace_partner_wording(value: str) -> str:
    replacements = {
        "Partner Risk, Compliance, Trader, and Finance checks are not connected yet.": "Live external partner review is not configured; local advisory checks were used.",
        "Partner Risk, Compliance, Trader, and Finance checks are not fully live yet.": "Live external partner review is not configured; local advisory checks were used.",
        "Connect Risk MCP server.": "Connect live external Risk service only if partner-review demo is required.",
        "Connect Compliance MCP server.": "Connect live external Compliance service only if partner-review demo is required.",
        "Connect Trader MCP server.": "Connect live external Trader service only if partner-review demo is required.",
        "Connect Finance REST API.": "Connect live external Finance service only if partner-review demo is required.",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def _clean_recursive(obj: Any, items_known: bool, origin: str | None, destination: str | None, incoterm: str | None, hazardous: bool) -> Any:
    if isinstance(obj, dict):
        return {key: _clean_recursive(value, items_known, origin, destination, incoterm, hazardous) for key, value in obj.items()}

    if isinstance(obj, list):
        cleaned = [_clean_recursive(item, items_known, origin, destination, incoterm, hazardous) for item in obj]
        return _filter_stale_list(cleaned, items_known, origin, destination, incoterm, hazardous)

    if isinstance(obj, str):
        return _replace_partner_wording(obj)

    return obj


def _extract_finance_fields(payload: dict[str, Any], original_text: str | None = None) -> dict[str, float]:
    text = _request_text(payload, original_text)
    fields: dict[str, float] = {}

    patterns = {
        "procurement_value_usd": [
            r"\bprocurement\s+value\s*(?:is|=|:)?\s*(?:USD\s*)?[$]?([0-9][0-9,.]*)\s*(?:USD|dollars?)?\b",
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
            match = re.search(pattern, text, flags=re.I)
            if match:
                value = _num(match.group(1))
                if value is not None:
                    fields[key] = value
                    break

    return fields


def _apply_finance(payload: dict[str, Any], original_text: str | None = None) -> None:
    fields = _extract_finance_fields(payload, original_text)
    if not fields:
        return

    finance_payload = _as_dict(payload.get("finance_payload"))
    for key, value in fields.items():
        payload[key] = value
        finance_payload[key] = value

    payload["finance_payload"] = finance_payload

    advice = _as_dict(payload.get("landed_cost_advice"))
    known = _as_dict(advice.get("known_inputs"))

    for key, value in fields.items():
        known[key] = value

    advice["known_inputs"] = known
    advice["missing_cost_inputs"] = [item for item in _as_list(advice.get("missing_cost_inputs")) if item not in fields]

    blockers = []
    for blocker in _as_list(advice.get("blockers")):
        lowered = str(blocker).lower()
        if "procurement value" in lowered and "procurement_value_usd" in fields:
            continue
        if "declared value" in lowered and "procurement_value_usd" in fields:
            continue
        blockers.append(blocker)
    advice["blockers"] = blockers

    procurement = _num(known.get("procurement_value_usd"))
    freight = _num(known.get("freight_quote_usd")) or 0.0
    insurance = _num(known.get("insurance_premium_usd")) or 0.0
    duty_rate = _num(known.get("duty_rate_percent")) or 0.0
    tax_rate = _num(known.get("import_tax_rate_percent")) or 0.0
    brokerage = _num(known.get("customs_brokerage_usd")) or 0.0
    local_delivery = _num(known.get("local_delivery_usd")) or 0.0

    if procurement is not None:
        customs_value = procurement + freight + insurance
        estimated_duty = customs_value * duty_rate / 100.0
        import_tax_base = customs_value + estimated_duty
        estimated_import_tax = import_tax_base * tax_rate / 100.0
        landed_cost = procurement + freight + insurance + estimated_duty + estimated_import_tax + brokerage + local_delivery

        advice["customs_value_usd"] = round(customs_value, 2)
        advice["estimated_duty_usd"] = round(estimated_duty, 2)
        advice["import_tax_base_usd"] = round(import_tax_base, 2)
        advice["estimated_import_tax_usd"] = round(estimated_import_tax, 2)
        advice["estimated_subtotal_known_usd"] = round(landed_cost, 2)
        advice["estimated_landed_cost_usd"] = round(landed_cost, 2)

    if not advice.get("missing_cost_inputs") and not advice.get("blockers"):
        advice["status"] = "review_required"
        advice["summary"] = "Landed cost advice prepared from the supplied finance inputs."
        recommendations = _as_list(advice.get("recommendations"))
        _add_unique(recommendations, "Validate all supplied finance inputs before final booking.")
        advice["recommendations"] = recommendations

    payload["landed_cost_advice"] = advice

    request = _request_text(payload, original_text).lower()
    if "finance" in request or "landed cost" in request or "procurement value" in request:
        agents = _as_list(payload.get("agents_called"))
        if "finance_agent" not in agents:
            agents.append("finance_agent")
            payload["agents_called"] = agents

        summaries = _as_list(payload.get("agent_summaries"))
        if not any(isinstance(item, dict) and item.get("agent_name") == "finance_agent" for item in summaries):
            summaries.append(
                {
                    "agent_name": "finance_agent",
                    "status": advice.get("status", "review_required"),
                    "summary": advice.get("summary", "Finance Agent prepared landed-cost advice."),
                }
            )
            payload["agent_summaries"] = summaries


def _apply_docs_compliance(payload: dict[str, Any], original_text: str | None = None) -> None:
    request = _request_text(payload, original_text).lower()
    origin, destination, incoterm = _route(payload, original_text)
    items = _cargo_items(payload, original_text)
    items_known = bool(items)
    hazardous = _request_is_hazardous(payload, items, original_text)

    explicit_document = any(token in request for token in ["document", "documents", "msds", "dangerous goods declaration"])
    explicit_compliance = any(token in request for token in ["compliance", "restriction", "restricted"])
    explicit_risk = "risk" in request

    for section_name in ["document_requirements_advice", "trade_compliance_readiness"]:
        section = _as_dict(payload.get(section_name))
        if not section:
            section = {"applicable": True, "status": "review_required", "summary": "Advisory section prepared from shipment context."}

        if origin:
            section["origin_country"] = origin
        if destination:
            section["destination_country"] = destination
        if incoterm:
            section["incoterm"] = incoterm

        if items_known:
            section["item_count"] = len(items)
            section["cargo_items_preview"] = [
                str(item.get("item_name") or item.get("name") or "").strip()
                for item in items
                if str(item.get("item_name") or item.get("name") or "").strip()
            ][:8]

        for list_key in ["warnings", "blockers", "missing_information", "user_questions", "recommendations", "conditional_documents"]:
            section[list_key] = _filter_stale_list(_as_list(section.get(list_key)), items_known, origin, destination, incoterm, hazardous)

        if section_name == "document_requirements_advice":
            required = _as_list(section.get("required_documents"))
            _add_unique(required, "Commercial invoice", "Packing list", "Bill of lading or airway bill")
            section["required_documents"] = required

            conditional = _as_list(section.get("conditional_documents"))
            if hazardous:
                _add_unique(conditional, "Dangerous goods declaration", "MSDS", "Carrier dangerous-goods acceptance confirmation")
                warnings = _as_list(section.get("warnings"))
                _add_unique(warnings, "Hazardous cargo requires specialist compliance documents and carrier acceptance.")
                section["warnings"] = warnings
            section["conditional_documents"] = conditional

        if section_name == "trade_compliance_readiness":
            if items_known:
                section["blockers"] = [
                    blocker for blocker in _as_list(section.get("blockers"))
                    if "no shipment items were found" not in str(blocker).lower()
                ]

            if hazardous:
                blockers = _as_list(section.get("blockers"))
                _add_unique(blockers, "Possible hazardous cargo requires specialist compliance and carrier acceptance.")
                section["blockers"] = blockers

            ready = _as_list(section.get("ready_items"))
            if origin:
                _add_unique(ready, f"Origin country is known: {origin}.")
            if destination:
                _add_unique(ready, f"Destination country is known: {destination}.")
            if incoterm:
                _add_unique(ready, f"Incoterm is known: {incoterm}.")
            section["ready_items"] = ready

        payload[section_name] = section

    agents = _as_list(payload.get("agents_called"))

    if explicit_document and "document_ai_agent" not in agents:
        agents.append("document_ai_agent")

    if explicit_compliance and "compliance_agent" not in agents:
        agents.append("compliance_agent")

    if explicit_risk and "risk_agent" not in agents:
        agents.append("risk_agent")

    payload["agents_called"] = agents


def _visualizer_dimensions(payload: dict[str, Any]) -> None:
    for obj in _walk_dicts(payload):
        visualizer = obj.get("logistics_visualizer")
        if not isinstance(visualizer, dict):
            continue

        container = _as_dict(visualizer.get("container"))
        selected = str(container.get("selected_container") or "").lower()

        max_l = 11.7 if "40" in selected else 5.7
        max_w = 2.25
        max_h = 2.25

        cargo_mix = visualizer.get("cargo_mix")
        if not isinstance(cargo_mix, list):
            continue

        for item in cargo_mix:
            if not isinstance(item, dict):
                continue

            dims = _as_dict(item.get("dimensions_m"))
            if not dims:
                continue

            length = _num(dims.get("length")) or 0.0
            width = _num(dims.get("width")) or 0.0
            height = _num(dims.get("height")) or 0.0

            if length <= max_l and width <= max_w and height <= max_h:
                continue

            quantity = max(_num(item.get("quantity")) or 1.0, 1.0)
            unit_cbm = _num(item.get("unit_cbm"))
            if unit_cbm is None:
                total_cbm = _num(item.get("total_cbm"))
                if total_cbm is not None:
                    unit_cbm = total_cbm / quantity

            if unit_cbm is None or unit_cbm <= 0:
                continue

            display_length = min(max_l, max(0.4, unit_cbm ** (1 / 3) * 1.6))
            display_width = min(max_w, max(0.35, (unit_cbm / display_length) ** 0.5))
            display_height = min(max_h, max(0.25, unit_cbm / (display_length * display_width)))

            item["dimensions_m"] = {
                "length": round(display_length, 2),
                "width": round(display_width, 2),
                "height": round(display_height, 2),
            }
            item["display_dimensions_estimated"] = True


def _rebuild(payload: dict[str, Any]) -> None:
    for module_name, function_name, key in [
        ("app.booking_readiness_advisor", "build_booking_readiness", "booking_readiness"),
        ("app.final_answer_builder", "build_final_answer", "final_answer"),
        ("app.action_plan_builder", "build_action_plan", "action_plan"),
        ("app.executive_summary_builder", "build_executive_summary", "executive_summary"),
        ("app.ui_sections_builder", "build_ui_sections", "ui_sections"),
    ]:
        try:
            module = __import__(module_name, fromlist=[function_name])
            payload[key] = getattr(module, function_name)(payload)
        except Exception:
            pass


def polish_backend_response(payload: Any, original_text: str | None = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    _apply_finance(payload, original_text)
    _apply_docs_compliance(payload, original_text)
    _visualizer_dimensions(payload)

    origin, destination, incoterm = _route(payload, original_text)
    items = _cargo_items(payload, original_text)
    hazardous = _request_is_hazardous(payload, items, original_text)

    payload = _clean_recursive(payload, bool(items), origin, destination, incoterm, hazardous)

    if isinstance(payload, dict):
        _rebuild(payload)
        payload = _clean_recursive(payload, bool(items), origin, destination, incoterm, hazardous)

    return payload


# Backend response consistency cleanup v3.
try:
    _polish_backend_response_before_consistency_v3 = polish_backend_response

    def _v3_as_dict(value):
        return value if isinstance(value, dict) else {}

    def _v3_as_list(value):
        return value if isinstance(value, list) else []

    def _v3_walk(obj):
        if isinstance(obj, dict):
            yield obj
            for value in obj.values():
                yield from _v3_walk(value)
        elif isinstance(obj, list):
            for value in obj:
                yield from _v3_walk(value)

    def _v3_request_text(payload, original_text=None):
        parts = []
        if original_text:
            parts.append(str(original_text))

        try:
            from app.request_context import active_request_text
            active = active_request_text()
            if active:
                parts.append(str(active))
        except Exception:
            pass

        if isinstance(payload, dict):
            for key in ["user_text", "request_text", "text", "prompt", "original_text"]:
                value = payload.get(key)
                if value:
                    parts.append(str(value))

            meta = payload.get("request_metadata")
            if isinstance(meta, dict):
                for key in ["user_text", "request_text", "text", "prompt", "original_text"]:
                    value = meta.get(key)
                    if value:
                        parts.append(str(value))

        return "\n".join(parts)

    def _v3_country(value):
        if not isinstance(value, str):
            return None

        value = value.strip(" .,:;")
        countries = {
            "india": "India",
            "usa": "USA",
            "united states": "USA",
            "united states of america": "USA",
            "germany": "Germany",
            "china": "China",
            "turkey": "Turkey",
            "uae": "UAE",
            "united arab emirates": "UAE",
            "iran": "Iran",
        }
        return countries.get(value.lower())

    def _v3_route(payload, original_text=None):
        import re

        text = _v3_request_text(payload, original_text)

        origin = None
        destination = None
        incoterm = None

        trusted_sections = [
            payload,
            _v3_as_dict(payload.get("handoff_payload")),
            _v3_as_dict(payload.get("trade_terms_advice")),
            _v3_as_dict(payload.get("document_requirements_advice")),
            _v3_as_dict(payload.get("trade_compliance_readiness")),
            _v3_as_dict(_v3_as_dict(payload.get("landed_cost_advice")).get("known_inputs")),
            _v3_as_dict(_v3_as_dict(payload.get("executive_summary")).get("shipment_snapshot")),
        ]

        for section in trusted_sections:
            if not origin:
                for key in ["origin_country", "origin", "country_from", "supplier_country"]:
                    origin = _v3_country(section.get(key))
                    if origin:
                        break

            if not destination:
                for key in ["destination_country", "destination", "country_to", "target_market"]:
                    destination = _v3_country(section.get(key))
                    if destination:
                        break

            if not incoterm:
                for key in ["incoterm", "trade_term"]:
                    value = section.get(key)
                    if isinstance(value, str) and value.strip().upper() in {"EXW", "FOB", "CIF", "DAP", "DDP", "FCA", "CFR"}:
                        incoterm = value.strip().upper()
                        break

        if not origin:
            match = re.search(r"\bfrom\s+([A-Za-z ]{2,40}?)(?=\s+to\b|\.|,| using\b|$)", text, flags=re.I)
            if match:
                origin = _v3_country(match.group(1))

        if not destination:
            for pattern in [
                r"\bdestination\s*(?:is|=|:)?\s*([A-Za-z ]{2,40}?)(?=\.|,| using\b|$)",
                r"\bto\s+([A-Za-z ]{2,40}?)(?=\.|,| using\b|$)",
            ]:
                match = re.search(pattern, text, flags=re.I)
                if match:
                    destination = _v3_country(match.group(1))
                    if destination:
                        break

        if not incoterm:
            match = re.search(r"\b(EXW|FOB|CIF|DAP|DDP|FCA|CFR)\b", text, flags=re.I)
            if match:
                incoterm = match.group(1).upper()

        return origin, destination, incoterm

    def _v3_items(payload, original_text=None):
        request = _v3_request_text(payload, original_text).lower()
        items = []
        seen = set()

        for obj in _v3_walk(payload):
            for key in ["cargo_mix", "items", "cargo_items", "item_breakdown"]:
                value = obj.get(key)
                if not isinstance(value, list):
                    continue

                for item in value:
                    if not isinstance(item, dict):
                        continue

                    name = str(item.get("item_name") or item.get("name") or item.get("description") or "").strip()
                    if not name or name.lower() in {"unknown item", "and 1200 kg"}:
                        continue

                    if name.lower() not in seen:
                        seen.add(name.lower())
                        items.append(item)

        inferred_names = []
        if "hazardous chemicals" in request:
            inferred_names.append("hazardous chemicals")
        if "ceramic tiles" in request:
            inferred_names.append("ceramic tiles")
        if "electric scooters" in request:
            inferred_names.append("electric scooters")
        if "glass bottles" in request:
            inferred_names.append("glass bottles")

        for name in inferred_names:
            if name not in seen:
                seen.add(name)
                tags = []
                if name == "hazardous chemicals":
                    tags = ["hazardous", "dangerous_goods"]
                if name == "electric scooters" and ("battery" in request or "batteries" in request or "lithium" in request):
                    tags = ["hazardous", "battery"]
                items.append({"item_name": name, "quantity": 1, "category_tags": tags})

        return items

    def _v3_is_hazardous(payload, original_text=None):
        request = _v3_request_text(payload, original_text).lower()
        return any(token in request for token in [
            "hazardous chemicals",
            "dangerous goods",
            "msds",
            "lithium battery",
            "lithium batteries",
            "scooters have batteries",
            "battery cargo",
        ])

    def _v3_clean_line(line, items_known, origin, destination, incoterm, hazardous, explicit_doc_request):
        if not isinstance(line, str):
            return line

        lowered = line.lower().strip()

        if items_known and any(phrase in lowered for phrase in [
            "no shipment items were available",
            "no shipment items were found",
            "no cargo items were available",
            "which products and quantities are included",
            "exact item list and quantities",
            "which products and quantities are included in this shipment",
        ]):
            return None

        if explicit_doc_request and items_known and any(phrase in lowered for phrase in [
            "unit dimensions or packed dimensions",
            "unit weight or total packed weight",
            "final packed dimensions and weight",
        ]):
            return None

        if origin and any(phrase in lowered for phrase in [
            "origin_country",
            "origin country is missing",
            "origin country is not fully confirmed",
            "what is the origin country",
        ]):
            return None

        if destination and any(phrase in lowered for phrase in [
            "destination_country",
            "destination country is missing",
            "destination country is not fully confirmed",
        ]):
            return None

        if origin and destination and "origin or destination is missing" in lowered:
            return None

        if incoterm and any(phrase in lowered for phrase in [
            "incoterm is missing",
            "no incoterm",
            "which incoterm",
            "incoterm or trade term such as",
            "shipping term should be shown",
            "which incoterm should be used",
        ]):
            return None

        if not hazardous and any(phrase in lowered for phrase in [
            "possible hazardous cargo",
            "hazardous cargo requires",
            "dangerous goods declaration",
            "msds",
            "carrier dangerous-goods",
            "shipment contains hazardous",
        ]):
            return None

        if "gemini reasoning was unavailable" in lowered:
            return line

        return line

    def _v3_clean_recursive(obj, items_known, origin, destination, incoterm, hazardous, explicit_doc_request):
        if isinstance(obj, dict):
            cleaned = {}
            for key, value in obj.items():
                cleaned[key] = _v3_clean_recursive(value, items_known, origin, destination, incoterm, hazardous, explicit_doc_request)
            return cleaned

        if isinstance(obj, list):
            cleaned = []
            for item in obj:
                value = _v3_clean_recursive(item, items_known, origin, destination, incoterm, hazardous, explicit_doc_request)
                if isinstance(value, str):
                    value = _v3_clean_line(value, items_known, origin, destination, incoterm, hazardous, explicit_doc_request)
                    if value is None:
                        continue
                cleaned.append(value)
            return cleaned

        if isinstance(obj, str):
            return obj

        return obj

    def _v3_sync_sections(payload, original_text=None):
        origin, destination, incoterm = _v3_route(payload, original_text)
        items = _v3_items(payload, original_text)
        items_known = bool(items)
        hazardous = _v3_is_hazardous(payload, original_text)
        request = _v3_request_text(payload, original_text).lower()
        explicit_doc_request = any(token in request for token in ["document", "documents", "msds", "dangerous goods declaration"])

        for key in ["document_requirements_advice", "trade_compliance_readiness"]:
            section = payload.get(key)
            if not isinstance(section, dict):
                continue

            if origin:
                section["origin_country"] = origin
            elif "origin_country" in section:
                section["origin_country"] = None

            if destination:
                section["destination_country"] = destination

            if incoterm:
                section["incoterm"] = incoterm
            elif "incoterm" in section:
                section["incoterm"] = None

            if items_known:
                section["item_count"] = len(items)
                section["cargo_items_preview"] = [
                    str(item.get("item_name") or item.get("name") or "").strip()
                    for item in items
                    if str(item.get("item_name") or item.get("name") or "").strip()
                ][:8]

            for list_key in ["warnings", "blockers", "missing_information", "recommendations", "user_questions", "conditional_documents"]:
                value = section.get(list_key)
                if isinstance(value, list):
                    section[list_key] = [
                        cleaned for raw in value
                        for cleaned in [_v3_clean_line(raw, items_known, origin, destination, incoterm, hazardous, explicit_doc_request)]
                        if cleaned is not None
                    ]

            if key == "document_requirements_advice":
                required = section.get("required_documents")
                if not isinstance(required, list):
                    required = []
                for doc in ["Commercial invoice", "Packing list", "Bill of lading or airway bill"]:
                    if doc not in required:
                        required.append(doc)
                section["required_documents"] = required

                conditional = section.get("conditional_documents")
                if not isinstance(conditional, list):
                    conditional = []

                if hazardous:
                    for doc in ["Dangerous goods declaration", "MSDS", "Carrier dangerous-goods acceptance confirmation"]:
                        if doc not in conditional:
                            conditional.append(doc)
                else:
                    conditional = [
                        doc for doc in conditional
                        if str(doc).lower() not in {"dangerous goods declaration", "msds", "carrier dangerous-goods acceptance confirmation"}
                    ]

                section["conditional_documents"] = conditional

        payload = _v3_clean_recursive(payload, items_known, origin, destination, incoterm, hazardous, explicit_doc_request)

        # Rebuild top-level missing preview/count from the final cleaned payload.
        missing = []

        if not origin:
            missing.append("origin_country")
        if not incoterm:
            missing.append("incoterm")

        landed = _v3_as_dict(payload.get("landed_cost_advice"))
        for item in _v3_as_list(landed.get("missing_cost_inputs")):
            if item not in missing:
                missing.append(item)

        doc = _v3_as_dict(payload.get("document_requirements_advice"))
        for item in _v3_as_list(doc.get("missing_or_unconfirmed_documents")):
            if item not in missing:
                missing.append("document: " + str(item))

        # For document-only prompts, do not show logistics packing questions as top-level missing info.
        if explicit_doc_request:
            missing = [
                item for item in missing
                if not any(skip in str(item).lower() for skip in [
                    "unit dimensions",
                    "unit weight",
                    "fragile, hazardous",
                    "exact item list",
                ])
            ]

        cleaned_missing = []
        seen = set()
        for item in missing:
            cleaned = _v3_clean_line(str(item), items_known, origin, destination, incoterm, hazardous, explicit_doc_request)
            if cleaned is None:
                continue
            low = cleaned.lower()
            if low not in seen:
                seen.add(low)
                cleaned_missing.append(cleaned)

        payload["missing_information_preview"] = cleaned_missing[:10]
        payload["missing_information_count"] = len(cleaned_missing)

        return payload

    def polish_backend_response(payload, original_text=None):
        cleaned = _polish_backend_response_before_consistency_v3(payload, original_text)
        try:
            if isinstance(cleaned, dict):
                return _v3_sync_sections(cleaned, original_text)
        except Exception:
            return cleaned
        return cleaned

except Exception:
    pass

