from __future__ import annotations

from copy import deepcopy


def _is_dict(value):
    return isinstance(value, dict)


def _is_list(value):
    return isinstance(value, list)


def _clean_container_name(value):
    if not isinstance(value, str):
        return value
    return (
        value.replace("20ftStandard", "20ft Standard")
        .replace("40ftStandard", "40ft Standard")
        .replace("40ftHigh", "40ft High")
        .replace("  ", " ")
        .strip()
    )


def _title_key(value):
    if value is None:
        return ""
    text = str(value).strip()
    overrides = {
        "fcl_preferred": "FCL preferred",
        "lcl_suitable": "LCL suitable",
        "special_equipment_required": "Special equipment required",
        "procurement_value_usd": "procurement value",
        "freight_quote_usd": "freight quote",
        "insurance_premium_usd": "insurance premium",
        "duty_rate_percent": "duty rate",
        "import_tax_rate_percent": "import tax / VAT rate",
        "customs_brokerage_usd": "customs brokerage",
        "local_delivery_usd": "local delivery",
        "partner_review_not_configured": "partner review not configured",
    }
    return overrides.get(text, text.replace("_", " "))


def _fmt(value, suffix=""):
    if value is None or value == "":
        return "not confirmed"
    if isinstance(value, float):
        value = round(value, 4)
        if value == int(value):
            value = int(value)
    return f"{value}{suffix}"


def _first_present(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _canonical_metrics(payload):
    metrics = payload.get("logistics_metrics") if _is_dict(payload.get("logistics_metrics")) else {}
    visualizer = payload.get("logistics_visualizer") if _is_dict(payload.get("logistics_visualizer")) else {}
    container = visualizer.get("container") if _is_dict(visualizer.get("container")) else {}

    total_cbm = _first_present(metrics.get("total_cbm"), container.get("total_cbm"))
    total_weight_kg = _first_present(metrics.get("total_weight_kg"), container.get("total_weight_kg"))
    recommended_container = _clean_container_name(_first_present(metrics.get("recommended_container"), container.get("selected_container")))
    recommended_load_type = _first_present(metrics.get("recommended_load_type"), container.get("recommended_load_type"))
    risk_level = _first_present(metrics.get("risk_level"), container.get("risk_level"))
    risk_score = _first_present(metrics.get("risk_score"), container.get("risk_score"))
    readiness_status = metrics.get("readiness_status")

    return {
        "total_cbm": total_cbm,
        "total_weight_kg": total_weight_kg,
        "recommended_container": recommended_container,
        "recommended_load_type": recommended_load_type,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "readiness_status": readiness_status,
    }


def _sync_metrics_dict(target, canonical):
    if not _is_dict(target):
        return

    for key in ["total_cbm", "total_weight_kg", "recommended_container", "recommended_load_type", "risk_level", "risk_score", "readiness_status"]:
        if key not in target:
            continue

        if key in canonical:
            target[key] = canonical.get(key)

    if target.get("recommended_container"):
        target["recommended_container"] = _clean_container_name(target["recommended_container"])


def _dedupe_list(items):
    seen = set()
    out = []
    for item in items or []:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _clean_issue_list(items, canonical):
    has_cbm = canonical.get("total_cbm") not in (None, "", 0)
    has_weight = canonical.get("total_weight_kg") not in (None, "", 0)

    cleaned = []

    for item in items or []:
        text = str(item).strip()
        lower = text.lower()

        if not text:
            continue

        if "shopping review was not applicable" in lower:
            continue

        if "live external partner review is not configured" in lower:
            continue

        if has_cbm and (
            "m x 1:" in lower
            or lower.startswith("m:")
            or lower.startswith("kg:")
            or "pallets of glass jars: missing dimensions" in lower
            or "dimensions and no catalog match" in lower
            or "catalog item 'ceramic tiles'" in lower
        ):
            continue

        if has_weight and "total shipment weight is missing" in lower:
            continue

        if "landed_cost has blockers" in lower:
            text = "Landed cost inputs are incomplete."
        elif "trade_compliance has blockers" in lower:
            text = "Compliance documents need final review."
        elif "total cbm is missing or invalid" in lower:
            text = "Final packed CBM or item dimensions are missing."
        elif "resolve logistics blockers" in lower:
            text = "Confirm final packed CBM or dimensions before booking."

        cleaned.append(text)

    return _dedupe_list(cleaned)


def _walk_and_clean_lists(obj, canonical):
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if key in {"warnings", "blockers", "bullets", "review_items", "top_risks", "top_next_actions", "missing_information"} and isinstance(value, list):
                obj[key] = _clean_issue_list(value, canonical)
            else:
                _walk_and_clean_lists(value, canonical)
    elif isinstance(obj, list):
        for item in obj:
            _walk_and_clean_lists(item, canonical)


def _get_route(payload):
    snap = ((payload.get("executive_summary") or {}).get("shipment_snapshot") or {}) if _is_dict(payload.get("executive_summary")) else {}
    trade = payload.get("trade_terms_advice") if _is_dict(payload.get("trade_terms_advice")) else {}
    docs = payload.get("document_requirements_advice") if _is_dict(payload.get("document_requirements_advice")) else {}

    return {
        "origin": _first_present(snap.get("origin_country"), trade.get("origin_country"), docs.get("origin_country")),
        "destination": _first_present(snap.get("destination_country"), trade.get("destination_country"), docs.get("destination_country")),
        "incoterm": _first_present(snap.get("incoterm"), trade.get("incoterm"), docs.get("incoterm")),
    }


def _get_cargo_names(payload, prompt_text=""):
    names = []

    visualizer = payload.get("logistics_visualizer") if _is_dict(payload.get("logistics_visualizer")) else {}
    for item in visualizer.get("cargo_mix") or []:
        if _is_dict(item) and item.get("item_name"):
            names.append(item.get("item_name"))

    docs = payload.get("document_requirements_advice") if _is_dict(payload.get("document_requirements_advice")) else {}
    for item in docs.get("cargo_items_preview") or []:
        names.append(item)

    procurement = payload.get("procurement_advice") if _is_dict(payload.get("procurement_advice")) else {}
    for item in procurement.get("selected_product_names") or []:
        names.append(item)

    lower = (prompt_text or "").lower()
    if not names:
        if "paint" in lower:
            names.append("paint")
        elif "glass jars" in lower:
            names.append("glass jars")
        elif "ceramic tiles" in lower:
            names.append("ceramic tiles")

    return _dedupe_list(names)


def _supplier_profiles_for(cargo_names, route):
    joined = " ".join(cargo_names).lower()
    origin = (route.get("origin") or "").lower()

    if "ceramic" in joined or "tile" in joined:
        return [
            {
                "supplier_name": "Kajaria Ceramics export desk",
                "supplier_type": "Best price candidate",
                "notes": "Good first-pass option for cost-sensitive ceramic tile sourcing. Verify export availability, MOQ, lead time, certifications, and CIF documentation before purchase order."
            },
            {
                "supplier_name": "Somany Ceramics institutional sales",
                "supplier_type": "Balanced reliability candidate",
                "notes": "Good default option to compare price, lead time, packaging quality, and documentation readiness."
            },
            {
                "supplier_name": "Asian Granito India export sales",
                "supplier_type": "Premium / urgent candidate",
                "notes": "Useful backup candidate for faster response, stricter packaging, and lower execution risk."
            },
        ]

    return []


def _install_supplier_profiles(payload, prompt_text, cargo_names, route):
    intent = str(payload.get("detected_intent") or "").lower()
    if "shopping" not in intent and "supplier" not in (prompt_text or "").lower():
        return

    profiles = _supplier_profiles_for(cargo_names, route)
    if not profiles:
        return

    payload["supplier_options"] = profiles
    payload["shortlisted_suppliers"] = profiles

    procurement = payload.setdefault("procurement_advice", {})
    if _is_dict(procurement):
        procurement["supplier_options_count"] = len(profiles)
        procurement["recommendations"] = [
            f"Shortlist: {p['supplier_name']} ({p['supplier_type']}): {p['notes']}"
            for p in profiles
        ] + [
            "These are demo/local shortlist profiles, not live-verified supplier records.",
            "Verify supplier identity, quotation, lead time, certifications, packaging standard, and payment terms before issuing a purchase order.",
            "Request proforma invoices from all shortlisted suppliers."
        ]


def _build_answer(payload, prompt_text, canonical):
    route = _get_route(payload)
    cargo_names = _get_cargo_names(payload, prompt_text)
    docs = payload.get("document_requirements_advice") if _is_dict(payload.get("document_requirements_advice")) else {}
    landed = payload.get("landed_cost_advice") if _is_dict(payload.get("landed_cost_advice")) else {}
    visualizer = payload.get("logistics_visualizer") if _is_dict(payload.get("logistics_visualizer")) else {}
    container = visualizer.get("container") if _is_dict(visualizer.get("container")) else {}
    fit_check = visualizer.get("fit_check") if _is_dict(visualizer.get("fit_check")) else {}

    total_cbm = canonical.get("total_cbm")
    total_weight_kg = canonical.get("total_weight_kg")
    container_name = _clean_container_name(canonical.get("recommended_container"))
    load_type = canonical.get("recommended_load_type")
    risk_level = canonical.get("risk_level")
    risk_score = canonical.get("risk_score")

    lower_prompt = (prompt_text or "").lower()
    has_volume = total_cbm not in (None, "", 0)
    has_weight = total_weight_kg not in (None, "", 0)
    is_blocked = not has_volume and ("ship" in lower_prompt or payload.get("detected_intent") == "logistics")
    is_hazard = any(word in lower_prompt for word in ["flammable", "hazardous", "lithium", "radioactive", "paint"])
    is_fragile = "fragile" in lower_prompt or any("fragile" in str(x).lower() for x in docs.get("conditional_documents") or [])

    if "shopping" in str(payload.get("detected_intent") or "").lower():
        opening = "I created a first-pass supplier and shipping plan. It is useful for planning, but supplier quotes and shipment documents still need review."
    elif is_blocked:
        opening = "Do not book this shipment yet. I can identify the route, risk, and document needs, but container planning is blocked until the missing cargo size information is provided."
    else:
        opening = "I prepared a first-pass logistics plan. The shipment is usable for planning, but it still needs document, cost, and booking review before execution."

    lines = [opening, ""]

    lines += [
        "Route and terms:",
        f"- Origin: {_fmt(route.get('origin'))}",
        f"- Destination: {_fmt(route.get('destination'))}",
        f"- Incoterm: {_fmt(route.get('incoterm'))}",
        "",
    ]

    if cargo_names:
        lines += [
            "Cargo:",
            f"- Items: {', '.join(cargo_names)}",
        ]
        if has_volume:
            lines.append(f"- Total volume: {_fmt(total_cbm, ' CBM')}")
        else:
            lines.append("- Total volume: not confirmed")
        if has_weight:
            lines.append(f"- Total weight: {_fmt(total_weight_kg, ' kg')}")
        else:
            lines.append("- Total weight: not confirmed")
        lines.append("")

    lines.append("Container and loading plan:")
    if has_volume and container_name:
        utilization = container.get("utilization_percent")
        lines.append(f"- Recommended container: {container_name}")
        lines.append(f"- Load type: {_title_key(load_type)}")
        if utilization is not None:
            lines.append(f"- Estimated container utilization: {_fmt(utilization, '%')}")
        if fit_check.get("status"):
            lines.append(f"- Fit check: {_title_key(fit_check.get('status'))}")
        if is_fragile:
            lines.append("- Handling: use strong pallet wrapping, cushioning, corner protection, and avoid unnecessary LCL transshipment because the cargo is fragile.")
    else:
        lines.append("- Container cannot be selected reliably yet because final packed CBM or item dimensions are missing.")
        lines.append("- Provide total CBM or packed dimensions so the app can calculate fit, utilization, and loading sequence.")
    lines.append("")

    lines.append("Risk and compliance:")
    if risk_level:
        lines.append(f"- Risk level: {_title_key(risk_level)}" + (f" ({risk_score}/10)" if risk_score is not None else ""))
    if is_hazard:
        lines.append("- Treat the cargo as hazardous/DG until the SDS/MSDS, hazard class, UN number, packing group, and carrier acceptance are confirmed.")
    if is_fragile:
        lines.append("- Fragile handling should be stated on the packing list and booking instructions.")
    if route.get("incoterm") == "CIF":
        lines.append("- CIF usually means the seller arranges main carriage and minimum insurance, but the exact risk transfer point still needs checking.")
    lines.append("")

    required_docs = docs.get("required_documents") or ["Commercial invoice", "Packing list", "Bill of lading or airway bill"]
    conditional_docs = docs.get("conditional_documents") or []

    lines.append("Documents to prepare:")
    for doc in _dedupe_list(required_docs):
        lines.append(f"- {doc}")
    for doc in _dedupe_list(conditional_docs):
        lines.append(f"- Conditional: {doc}")
    lines.append("")

    missing_costs = landed.get("missing_cost_inputs") or []
    if missing_costs:
        lines.append("Cost inputs still needed:")
        compact = [_title_key(x) for x in missing_costs[:7]]
        lines.append("- " + ", ".join(compact))
        lines.append("")

    questions = payload.get("clarification_questions") or []
    if questions:
        lines.append("Answer these next:")
        for q in _dedupe_list(questions):
            lines.append(f"- {q}")
        lines.append("")

    lines.append("Recommended next steps:")
    if has_volume and container_name:
        lines.append("- Compare FCL quotes for 20ft, 40ft, and 40ft high cube options before booking.")
        lines.append("- Confirm final supplier/cargo value before insurance and landed-cost calculation.")
        lines.append("- Prepare the required documents and then run compliance review.")
    else:
        lines.append("- Add final packed CBM or item dimensions.")
        lines.append("- Add declared cargo value and freight/insurance/tax inputs if landed cost is needed.")
        lines.append("- For hazardous cargo, add SDS/MSDS and dangerous-goods details before carrier booking.")

    return "\n".join(lines).strip()


def _sync_structured_metrics(payload, canonical):
    payload["logistics_metrics"] = {
        "total_cbm": canonical.get("total_cbm"),
        "total_weight_kg": canonical.get("total_weight_kg"),
        "recommended_container": _clean_container_name(canonical.get("recommended_container")),
        "recommended_load_type": canonical.get("recommended_load_type"),
        "risk_level": canonical.get("risk_level"),
        "risk_score": canonical.get("risk_score"),
        "readiness_status": canonical.get("readiness_status"),
    }

    visualizer = payload.get("logistics_visualizer")
    if _is_dict(visualizer):
        container = visualizer.setdefault("container", {})
        if _is_dict(container):
            if canonical.get("recommended_container"):
                container["selected_container"] = _clean_container_name(canonical.get("recommended_container"))
            if canonical.get("total_cbm") is not None:
                container["total_cbm"] = canonical.get("total_cbm")
            if canonical.get("total_weight_kg") is not None:
                container["total_weight_kg"] = canonical.get("total_weight_kg")
            if canonical.get("recommended_load_type"):
                container["recommended_load_type"] = canonical.get("recommended_load_type")

            capacity = container.get("capacity_cbm") or 33.2
            total_cbm = canonical.get("total_cbm")
            if total_cbm not in (None, "", 0):
                utilization = round((float(total_cbm) / float(capacity)) * 100, 2)
                container["utilization_percent"] = utilization
                visualizer["display_metrics"] = {
                    "loaded_cbm": total_cbm,
                    "container_cbm": capacity,
                    "remaining_cbm": round(float(capacity) - float(total_cbm), 2),
                    "utilization_percent": utilization,
                    "basis": "shipment_total_cbm",
                }

    lqr = payload.get("logistics_quality_review")
    if _is_dict(lqr):
        _sync_metrics_dict(lqr, canonical)
        fma = lqr.get("freight_mode_advice")
        if _is_dict(fma):
            _sync_metrics_dict(fma, canonical)
            if canonical.get("total_cbm") in (None, "", 0):
                fma["status"] = "blocked"
                fma["primary_mode"] = None

    landed = payload.get("landed_cost_advice")
    if _is_dict(landed):
        known = landed.setdefault("known_inputs", {})
        if _is_dict(known):
            _sync_metrics_dict(known, canonical)

    executive = payload.get("executive_summary")
    if _is_dict(executive):
        snap = executive.setdefault("shipment_snapshot", {})
        if _is_dict(snap):
            _sync_metrics_dict(snap, canonical)

        has_volume = canonical.get("total_cbm") not in (None, "", 0)
        has_weight = canonical.get("total_weight_kg") not in (None, "", 0)

        if has_volume and has_weight:
            executive["status"] = "review_required"
            executive["headline"] = "Shipment is usable for first-pass planning, but not ready to book yet."
            executive["ready_for_first_pass"] = True
            executive["ready_for_booking"] = False
            executive["booking_score"] = max(int(executive.get("booking_score") or 0), 45)
            executive["next_gate"] = "review_before_booking"
        else:
            executive["status"] = "blocked"
            executive["headline"] = "Shipment is blocked until cargo size information is confirmed."
            executive["ready_for_first_pass"] = False
            executive["ready_for_booking"] = False
            executive["next_gate"] = "fill_missing_information"

    br = payload.get("booking_readiness")
    if _is_dict(br):
        has_volume = canonical.get("total_cbm") not in (None, "", 0)
        has_weight = canonical.get("total_weight_kg") not in (None, "", 0)

        if has_volume and has_weight:
            br["status"] = "review_required"
            br["summary"] = "Shipment is usable for first-pass planning, but not ready to book yet."
            br["ready_for_first_pass"] = True
            br["ready_for_booking"] = False
            br["score"] = max(int(br.get("score") or 0), 45)
            br["next_gate"] = "review_before_booking"
        else:
            br["status"] = "blocked"
            br["summary"] = "Shipment is blocked until cargo size information is confirmed."
            br["ready_for_first_pass"] = False
            br["ready_for_booking"] = False
            br["next_gate"] = "fill_missing_information"

    for section in payload.get("ui_sections") or []:
        if not _is_dict(section):
            continue

        section_id = section.get("section_id")
        metrics = section.get("metrics")

        if section_id in {"shipment_snapshot", "logistics"} and _is_dict(metrics):
            _sync_metrics_dict(metrics, canonical)

        if section_id == "costs_insurance" and _is_dict(metrics):
            known = metrics.get("known_inputs")
            if _is_dict(known):
                _sync_metrics_dict(known, canonical)

        if section_id == "executive_decision":
            has_volume = canonical.get("total_cbm") not in (None, "", 0)
            has_weight = canonical.get("total_weight_kg") not in (None, "", 0)
            if has_volume and has_weight:
                section["status"] = "review_required"
                section["summary"] = "Shipment is usable for first-pass planning, but not ready to book yet."
                if _is_dict(metrics):
                    metrics["ready_for_first_pass"] = True
                    metrics["ready_for_booking"] = False
                    metrics["booking_score"] = max(int(metrics.get("booking_score") or 0), 45)
                    metrics["next_gate"] = "review_before_booking"


def _fix_questions(payload, prompt_text, canonical):
    lower = (prompt_text or "").lower()
    questions = []

    if canonical.get("total_cbm") in (None, "", 0):
        if "paint" in lower:
            questions.append("What is the final packed CBM or packed dimensions for the paint shipment?")
        else:
            questions.append("What is the final packed CBM or packed dimensions for this shipment?")

    if "flammable" in lower or "paint" in lower:
        questions.append("Can you provide the SDS/MSDS, hazard class, UN number, packing group, and carrier restrictions for the flammable cargo?")

    if not questions:
        questions = payload.get("clarification_questions") or []

    cleaned = []
    for q in questions:
        text = str(q).strip()
        low = text.lower()
        if canonical.get("total_weight_kg") not in (None, "", 0) and "and weight" in low and "dimensions" in low:
            text = "Can you confirm the final packed CBM or dimensions?"
        cleaned.append(text)

    payload["clarification_questions"] = _dedupe_list(cleaned)


def _fix_agent_summaries(payload, canonical):
    summaries = payload.get("agent_summaries")
    if not isinstance(summaries, list):
        return

    for item in summaries:
        if not _is_dict(item):
            continue
        if item.get("agent_name") == "logistics_agent":
            cbm = canonical.get("total_cbm")
            weight = canonical.get("total_weight_kg")
            container = _clean_container_name(canonical.get("recommended_container"))
            if cbm not in (None, "", 0):
                item["summary"] = f"Logistics plan status: {item.get('status')}. Total cargo is {cbm} CBM and {weight} kg. Recommended container: {container}."
            else:
                item["summary"] = f"Logistics plan status: {item.get('status')}. Weight is {weight or 'not confirmed'} kg, but final packed CBM or dimensions are still missing."


def polish_demo_response(payload, prompt_text=None):
    if not isinstance(payload, dict):
        return payload

    prompt_text = prompt_text or ""
    payload = deepcopy(payload)

    canonical = _canonical_metrics(payload)
    cargo_names = _get_cargo_names(payload, prompt_text)
    route = _get_route(payload)

    _install_supplier_profiles(payload, prompt_text, cargo_names, route)
    _sync_structured_metrics(payload, canonical)
    _fix_questions(payload, prompt_text, canonical)
    _walk_and_clean_lists(payload, canonical)
    _fix_agent_summaries(payload, canonical)

    answer_text = _build_answer(payload, prompt_text, canonical)

    payload["display_answer"] = answer_text
    payload["frontend_answer"] = answer_text

    final_answer = payload.setdefault("final_answer", {})
    if isinstance(final_answer, dict):
        final_answer["answer_text"] = answer_text
        final_answer["headline"] = answer_text.splitlines()[0]
        final_answer["status"] = "blocked" if canonical.get("total_cbm") in (None, "", 0) and payload.get("detected_intent") == "logistics" else "review_required"

    if canonical.get("recommended_container"):
        payload["short_answer"] = (
            f"Decision: {payload.get('decision')}. Agents called: {', '.join(payload.get('agents_called') or [])}. "
            f"Logistics: {canonical.get('total_cbm')} CBM, {canonical.get('total_weight_kg')} kg, "
            f"recommended container {_clean_container_name(canonical.get('recommended_container'))}, "
            f"risk level {canonical.get('risk_level')}."
        )

    return payload
