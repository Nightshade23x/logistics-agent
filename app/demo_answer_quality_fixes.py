from __future__ import annotations


import re
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




def _ux_is_dict(value):
    return isinstance(value, dict)


def _ux_number(value):
    try:
        if value in (None, "", [], {}):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _ux_fmt_number(value):
    number = _ux_number(value)

    if number is None:
        return "not confirmed"

    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))

    return f"{number:.2f}".rstrip("0").rstrip(".")


def _ux_unique(values):
    output = []
    seen = set()

    for value in values or []:
        if value in (None, ""):
            continue

        value = str(value).strip()

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        output.append(value)

    return output


def _ux_best_docs(payload):
    candidates = []

    top = payload.get("document_requirements_advice")

    if _ux_is_dict(top):
        candidates.append(top)

    specialist_responses = payload.get("specialist_responses")

    if _ux_is_dict(specialist_responses):
        document_response = specialist_responses.get(
            "document_ai_agent"
        )

        if _ux_is_dict(document_response):
            specialist_docs = document_response.get(
                "document_requirements_advice"
            )

            if _ux_is_dict(specialist_docs):
                candidates.append(specialist_docs)

    if not candidates:
        return {}

    def score(candidate):
        return (
            3 * len(candidate.get("conditional_documents") or [])
            + 2 * len(candidate.get("required_documents") or [])
            + 2 * len(candidate.get("cargo_items_preview") or [])
            + len(candidate.get("recommendations") or [])
        )

    return max(candidates, key=score)


def _ux_cargo_names(payload, prompt_text):
    values = []

    generic = {
        "",
        "cargo",
        "item",
        "items",
        "product",
        "requested product",
        "requested cargo",
        "unknown",
        "unknown cargo",
        "m",
        "cm",
        "mm",
        "kg",
    }

    def add(value):
        if value is None:
            return

        value = str(value).strip(" \t\r\n,.;:-")

        if not value:
            return

        if value.lower() in generic:
            return

        if len(value) <= 1:
            return

        values.append(value)

    docs = _ux_best_docs(payload)

    for value in docs.get("cargo_items_preview") or []:
        add(value)

    specialist_responses = payload.get("specialist_responses")

    if _ux_is_dict(specialist_responses):
        doc_agent = specialist_responses.get(
            "document_ai_agent"
        )

        if _ux_is_dict(doc_agent):
            specialist_docs = doc_agent.get(
                "document_requirements_advice"
            )

            if _ux_is_dict(specialist_docs):
                for value in (
                    specialist_docs.get("cargo_items_preview")
                    or []
                ):
                    add(value)

    visualizer = payload.get("logistics_visualizer")

    if _ux_is_dict(visualizer):
        for item in visualizer.get("cargo_mix") or []:
            if not _ux_is_dict(item):
                continue

            add(
                item.get("item_name")
                or item.get("name")
                or item.get("product_name")
            )

    prompt = str(prompt_text or "")

    patterns = [
        r"\b\d+(?:\.\d+)?\s*CBM\s+(.+?)\s+from\s+",
        r"\b\d+\s+pallets?\s+of\s+(.+?)\s+from\s+",
        r"\bship\s+\d+\s+pallets?\s+of\s+(.+?)\s+from\s+",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            prompt,
            flags=re.IGNORECASE,
        )

        if match:
            add(match.group(1))
            break

    return _ux_unique(values) or ["requested cargo"]


def _ux_route(payload):
    origin = (
        payload.get("origin_country")
        or payload.get("origin")
    )

    destination = (
        payload.get("destination_country")
        or payload.get("destination")
    )

    incoterm = None

    trade_terms = payload.get("trade_terms_advice")

    if _ux_is_dict(trade_terms):
        origin = (
            trade_terms.get("origin_country")
            or origin
        )

        destination = (
            trade_terms.get("destination_country")
            or destination
        )

        incoterm = trade_terms.get("incoterm")

    incoterm = (
        incoterm
        or payload.get("incoterm")
        or payload.get("trade_term")
    )

    handoff = payload.get("handoff_payload")

    if _ux_is_dict(handoff):
        origin = (
            origin
            or handoff.get("origin_country")
            or handoff.get("origin")
        )

        destination = (
            destination
            or handoff.get("destination_country")
            or handoff.get("destination")
        )

        incoterm = (
            incoterm
            or handoff.get("incoterm")
            or handoff.get("trade_term")
        )

    return {
        "origin": origin,
        "destination": destination,
        "incoterm": incoterm,
    }


def _ux_trader_details(payload):
    texts = []

    for summary in payload.get("agent_summaries") or []:

        if not _ux_is_dict(summary):
            continue

        if (
            str(summary.get("agent_name") or "").lower()
            == "trader_agent"
        ):
            value = summary.get("summary")

            if value:
                texts.append(str(value))

    specialist_responses = payload.get(
        "specialist_responses"
    )

    trader_response = {}

    if _ux_is_dict(specialist_responses):

        candidate = specialist_responses.get(
            "trader_agent"
        )

        if _ux_is_dict(candidate):
            trader_response = candidate

            if candidate.get("summary"):
                texts.append(
                    str(candidate.get("summary"))
                )

    combined = " ".join(texts)

    duty_rate = None

    def walk(value):
        nonlocal duty_rate

        if duty_rate is not None:
            return

        if isinstance(value, dict):

            for key, item in value.items():

                if str(key).lower() in {
                    "duty_rate_percent",
                    "estimated_duty_rate_percent",
                    "import_duty_rate_percent",
                    "duty_rate",
                }:
                    number = _ux_number(item)

                    if number is not None:
                        duty_rate = number
                        return

            for item in value.values():
                walk(item)

        elif isinstance(value, list):

            for item in value:
                walk(item)

    walk(trader_response)

    if duty_rate is None:
        match = re.search(
            r"(?:estimated\s+)?duty\s+rate"
            r"(?:\s+of|\s*:)?\s*"
            r"([0-9]+(?:\.[0-9]+)?)\s*%",
            combined,
            flags=re.IGNORECASE,
        )

        if match:
            duty_rate = float(match.group(1))

    lower = combined.lower()

    provisional = any(
        phrase in lower
        for phrase in [
            "could not be automatically classified",
            "default duty rate was used",
            "fallback duty rate",
            "fallback rate",
            "default rate",
        ]
    )

    no_fta = any(
        phrase in lower
        for phrase in [
            "no known free trade agreement applies",
            "no known fta applies",
            "no free trade agreement applies",
        ]
    )

    return {
        "duty_rate_percent": duty_rate,
        "provisional": provisional,
        "no_known_fta": no_fta,
        "summary": combined,
    }


def _full_trade_plan_requested_v2(prompt_text, payload):
    lower = str(prompt_text or "").lower()

    if any(
        phrase in lower
        for phrase in [
            "full trade plan",
            "complete trade plan",
            "end-to-end trade plan",
            "full shipment plan",
            "complete shipment plan",
        ]
    ):
        return True

    groups = [
        ["logistics", "shipment", "container"],
        ["document", "documents"],
        ["duty", "tariff", "hs code"],
        ["risk", "compliance"],
        ["landed cost", "cost", "insurance"],
    ]

    hits = sum(
        1
        for group in groups
        if any(term in lower for term in group)
    )

    agents = {
        str(agent).lower()
        for agent in payload.get("agents_called") or []
    }

    specialist_count = len(
        agents.intersection(
            {
                "logistics_agent",
                "trader_agent",
                "document_ai_agent",
                "risk_agent",
                "finance_agent",
                "compliance_agent",
            }
        )
    )

    return hits >= 4 and specialist_count >= 3


def _ux_cost_name(value):
    mapping = {
        "procurement_value_usd":
            "declared / cargo value",

        "cargo_value_usd":
            "declared / cargo value",

        "freight_quote_usd":
            "freight quote",

        "insurance_premium_usd":
            "insurance premium",

        "duty_rate_percent":
            "final duty rate",

        "import_tax_rate_percent":
            "applicable import tax rate",

        "vat_rate_percent":
            "applicable import tax / VAT rate",

        "customs_brokerage_usd":
            "customs brokerage / clearance fee",

        "local_delivery_usd":
            "destination local delivery",
    }

    return mapping.get(
        str(value),
        str(value).replace("_", " "),
    )


def _build_full_trade_answer_v2(
    payload,
    prompt_text,
    canonical,
):
    route = _ux_route(payload)
    cargo_names = _ux_cargo_names(
        payload,
        prompt_text,
    )

    docs = _ux_best_docs(payload)
    trader = _ux_trader_details(payload)

    landed = payload.get("landed_cost_advice")

    if not _ux_is_dict(landed):
        landed = {}

    visualizer = payload.get(
        "logistics_visualizer"
    )

    if not _ux_is_dict(visualizer):
        visualizer = {}

    container_data = visualizer.get(
        "container"
    )

    if not _ux_is_dict(container_data):
        container_data = {}

    display_metrics = visualizer.get(
        "display_metrics"
    )

    if not _ux_is_dict(display_metrics):
        display_metrics = {}

    total_cbm = (
        canonical.get("total_cbm")
        if isinstance(canonical, dict)
        else None
    )

    total_weight = (
        canonical.get("total_weight_kg")
        if isinstance(canonical, dict)
        else None
    )

    container_name = (
        canonical.get("recommended_container")
        if isinstance(canonical, dict)
        else None
    )

    load_type = (
        canonical.get("recommended_load_type")
        if isinstance(canonical, dict)
        else None
    )

    risk_level = (
        canonical.get("risk_level")
        if isinstance(canonical, dict)
        else None
    )

    risk_score = (
        canonical.get("risk_score")
        if isinstance(canonical, dict)
        else None
    )

    utilization = (
        container_data.get("utilization_percent")
        or display_metrics.get(
            "utilization_percent"
        )
    )

    required_docs = (
        docs.get("required_documents")
        or [
            "Commercial invoice",
            "Packing list",
            "Bill of lading or airway bill",
        ]
    )

    conditional_docs = (
        docs.get("conditional_documents")
        or []
    )

    missing_docs = (
        docs.get(
            "missing_or_unconfirmed_documents"
        )
        or []
    )

    missing_costs = list(
        landed.get("missing_cost_inputs")
        or []
    )

    duty_rate = trader.get(
        "duty_rate_percent"
    )

    # Trader already has an estimate.
    # Do not tell the user simultaneously that
    # "duty rate is missing".
    if duty_rate is not None:

        missing_costs = [
            value
            for value in missing_costs
            if str(value) != "duty_rate_percent"
        ]

    physically_workable = (
        _ux_number(total_cbm) not in (None, 0)
        and
        _ux_number(total_weight) not in (None, 0)
        and
        bool(container_name)
    )

    still_open = bool(
        missing_costs
        or missing_docs
        or trader.get("provisional")
    )

    if physically_workable and still_open:

        opening = (
            "First-pass verdict: this shipment is physically "
            "workable, but it is not ready to book yet. "
            "The logistics plan is usable; tariff "
            "classification, commercial cost inputs, and "
            "shipment documents still need confirmation."
        )

    elif physically_workable:

        opening = (
            "First-pass verdict: the shipment is physically "
            "workable and the main planning inputs are "
            "available. Complete the final document and "
            "compliance checks before booking."
        )

    else:

        opening = (
            "First-pass verdict: the trade route can be "
            "reviewed, but the shipment is not ready for "
            "booking because important planning inputs are "
            "still missing."
        )

    lines = [
        opening,
        "",
        "Shipment plan:",
        f"- Cargo: {', '.join(cargo_names)}",
        f"- Route: "
        f"{route.get('origin') or 'not confirmed'} → "
        f"{route.get('destination') or 'not confirmed'}",
        f"- Incoterm: "
        f"{route.get('incoterm') or 'not confirmed'}",
    ]

    if _ux_number(total_cbm) is not None:
        lines.append(
            "- Total volume: "
            + _ux_fmt_number(total_cbm)
            + " CBM"
        )

    if _ux_number(total_weight) is not None:
        lines.append(
            "- Total weight: "
            + _ux_fmt_number(total_weight)
            + " kg"
        )

    if container_name:
        lines.append(
            f"- Recommended container: "
            f"{container_name}"
        )

    if load_type:
        human_load_type = (
            str(load_type)
            .replace("_", " ")
            .upper()
        )

        lines.append(
            f"- Recommended load type: "
            f"{human_load_type}"
        )

    if _ux_number(utilization) is not None:
        lines.append(
            "- Estimated container utilization: "
            + _ux_fmt_number(utilization)
            + "%"
        )

    lines.extend(
        [
            "",
            "Duty and trade treatment:",
        ]
    )

    if duty_rate is not None:

        lines.append(
            "- Current duty estimate: approximately "
            + _ux_fmt_number(duty_rate)
            + "%."
        )

        if trader.get("provisional"):

            lines.append(
                "- Important: this duty figure is provisional. "
                "The Trader Agent could not confirm the final "
                "product classification and used a fallback/"
                "default tariff rate. Confirm the ceramic-tile "
                "HS classification before customs entry or "
                "final costing."
            )

        else:

            lines.append(
                "- Confirm the final HS classification before "
                "customs entry even if the current duty rate "
                "remains unchanged."
            )

    else:

        lines.append(
            "- A reliable final duty rate is not available yet. "
            "Confirm the HS code / tariff classification before "
            "customs entry and final costing."
        )

    if trader.get("no_known_fta"):

        lines.append(
            "- FTA: the Trader Agent did not identify a known "
            "free-trade agreement applying to this India–USA "
            "shipment."
        )

    incoterm = str(
        route.get("incoterm") or ""
    ).upper()

    if incoterm == "CIF":

        lines.extend(
            [
                "",
                "CIF responsibilities:",
                "- The seller normally arranges the main "
                "carriage and minimum cargo insurance.",
                "- Confirm the exact risk-transfer point and "
                "the actual insurance coverage. CIF does not "
                "automatically mean the seller carries transit "
                "risk all the way to the final destination.",
            ]
        )

    lines.extend(
        [
            "",
            "Documents and compliance:",
        ]
    )

    for doc in _ux_unique(required_docs):
        lines.append(
            f"- Required: {doc}"
        )

    for doc in _ux_unique(conditional_docs):
        lines.append(
            f"- Check / conditional: {doc}"
        )

    if missing_docs:

        lines.append(
            "- Current status: required shipment documents "
            "are still missing or unconfirmed, so compliance "
            "is not final."
        )

    lines.extend(
        [
            "",
            "Risk:",
        ]
    )

    if risk_level:

        risk_text = (
            str(risk_level)
            .replace("_", " ")
            .lower()
        )

        if _ux_number(risk_score) is not None:

            lines.append(
                "- Current operational/logistics risk: "
                f"{risk_text} "
                f"({_ux_fmt_number(risk_score)}/10)."
            )

        else:

            lines.append(
                "- Current operational/logistics risk: "
                f"{risk_text}."
            )

    else:

        lines.append(
            "- Operational logistics risk has not been "
            "fully scored."
        )

    if (
        trader.get("provisional")
        or missing_docs
        or missing_costs
    ):

        lines.append(
            "- This does not mean the entire trade is cleared "
            "or low-risk. Tariff, document, insurance, and "
            "commercial checks remain open."
        )

    lines.extend(
        [
            "",
            "Landed cost:",
        ]
    )

    subtotal = landed.get(
        "estimated_subtotal_known_usd"
    )

    if _ux_number(subtotal) is not None:

        lines.append(
            "- Currently calculable subtotal: "
            + _ux_fmt_number(subtotal)
            + " USD."
        )

    else:

        lines.append(
            "- A final landed-cost figure cannot yet be "
            "calculated from the information provided."
        )

    if missing_costs:

        cost_labels = _ux_unique(
            [
                _ux_cost_name(value)
                for value in missing_costs
            ]
        )

        lines.append(
            "- Still needed: "
            + ", ".join(cost_labels)
            + "."
        )

    if (
        duty_rate is not None
        and trader.get("provisional")
    ):

        lines.append(
            "- Do not treat the current "
            + _ux_fmt_number(duty_rate)
            + "% duty estimate as final until the HS "
            "classification is confirmed."
        )

    if incoterm == "CIF":

        lines.append(
            "- Even though CIF normally includes seller-"
            "arranged freight and minimum insurance, obtain "
            "the actual freight and insurance values used for "
            "the final customs / landed-cost calculation."
        )

    lines.extend(
        [
            "",
            "What this means:",
        ]
    )

    if physically_workable:

        lines.append(
            "- The current container plan is usable for "
            "quoting and first-pass shipment planning."
        )

    if still_open:

        lines.append(
            "- Do not treat this shipment as booking-ready, "
            "customs-cleared, or fully costed until the open "
            "checks above are resolved."
        )

    lines.extend(
        [
            "",
            "Next actions, in order:",
        ]
    )

    step = 1

    if (
        trader.get("provisional")
        or duty_rate is None
    ):

        lines.append(
            f"- {step}) Confirm the ceramic-tile HS "
            "classification and final duty rate."
        )
        step += 1

    if missing_costs:

        lines.append(
            f"- {step}) Confirm the declared cargo value and "
            "the remaining freight, insurance, tax, "
            "brokerage, and local-delivery inputs required "
            "for landed cost."
        )
        step += 1

    if required_docs or conditional_docs:

        lines.append(
            f"- {step}) Prepare the required shipment "
            "documents and verify the conditional origin/"
            "insurance documents."
        )
        step += 1

    if physically_workable and container_name:

        lines.append(
            f"- {step}) Obtain the freight quote for the "
            f"recommended {container_name} and confirm final "
            "packed dimensions before booking."
        )
        step += 1

    lines.append(
        f"- {step}) Rerun landed-cost and compliance checks. "
        "Once those are clear, proceed to final booking."
    )


    # FULL_TRADE_REPORT_SYNC_V3
    #
    # The user-facing answer and the exported JSON should tell
    # the same story. The original pipeline can contain richer
    # specialist data alongside older generic top-level fields.
    # Synchronize those fields here for full-trade requests.

    # --------------------------------------------------------
    # A. Synchronize the real product name
    # --------------------------------------------------------

    primary_cargo_name = (
        cargo_names[0]
        if cargo_names
        else "requested cargo"
    )

    visualizer_sync = payload.get(
        "logistics_visualizer"
    )

    if isinstance(visualizer_sync, dict):

        cargo_mix_sync = visualizer_sync.get(
            "cargo_mix"
        )

        if isinstance(cargo_mix_sync, list):

            generic_names = {
                "",
                "cargo",
                "item",
                "product",
                "requested cargo",
                "requested product",
            }

            for cargo_item in cargo_mix_sync:

                if not isinstance(cargo_item, dict):
                    continue

                current_name = str(
                    cargo_item.get("item_name")
                    or ""
                ).strip()

                if current_name.lower() in generic_names:

                    cargo_item[
                        "item_name"
                    ] = primary_cargo_name


    # --------------------------------------------------------
    # B. Promote richer Document Agent output
    # --------------------------------------------------------

    top_docs_sync = payload.setdefault(
        "document_requirements_advice",
        {},
    )

    if isinstance(top_docs_sync, dict):

        top_docs_sync["applicable"] = True

        top_docs_sync[
            "cargo_items_preview"
        ] = list(cargo_names)

        top_docs_sync[
            "required_documents"
        ] = _ux_unique(
            required_docs
        )

        top_docs_sync[
            "conditional_documents"
        ] = _ux_unique(
            conditional_docs
        )

        if missing_docs:

            top_docs_sync[
                "missing_or_unconfirmed_documents"
            ] = _ux_unique(
                missing_docs
            )


    # --------------------------------------------------------
    # C. Synchronize compliance cargo/docs
    # --------------------------------------------------------

    compliance_sync = payload.get(
        "trade_compliance_readiness"
    )

    if isinstance(compliance_sync, dict):

        compliance_sync[
            "cargo_items_preview"
        ] = list(cargo_names)

        compliance_sync[
            "conditional_documents"
        ] = _ux_unique(
            conditional_docs
        )


    # --------------------------------------------------------
    # D. Fix false "No Logistics Agent response"
    # --------------------------------------------------------

    logistics_review_sync = payload.setdefault(
        "logistics_quality_review",
        {},
    )

    if (
        isinstance(logistics_review_sync, dict)
        and (
            _ux_number(total_cbm) is not None
            or _ux_number(total_weight) is not None
            or container_name
        )
    ):

        logistics_review_sync.update(
            {
                "applicable": True,
                "status": "review_required",
                "summary": (
                    "Logistics planning output is available "
                    "and usable for first-pass shipment review."
                ),
                "total_cbm": total_cbm,
                "total_weight_kg": total_weight,
                "recommended_container": container_name,
                "recommended_load_type": load_type,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "readiness_status": (
                    canonical.get(
                        "readiness_status"
                    )
                    if isinstance(
                        canonical,
                        dict,
                    )
                    else None
                ),
            }
        )


    # --------------------------------------------------------
    # E. Store Trader output in a structured report section
    # --------------------------------------------------------

    trade_duty_sync = payload.setdefault(
        "trade_duty_advice",
        {},
    )

    if isinstance(trade_duty_sync, dict):

        if duty_rate is not None:

            duty_summary = (
                "Trader Agent estimated duty at "
                + _ux_fmt_number(duty_rate)
                + "%."
            )

            if trader.get("provisional"):

                duty_summary += (
                    " This rate is provisional because "
                    "the final HS classification was "
                    "not confirmed."
                )

        else:

            duty_summary = (
                "Final duty could not be confirmed "
                "because HS classification remains open."
            )

        trade_duty_sync.update(
            {
                "applicable": True,
                "status": (
                    "review_required"
                    if (
                        trader.get("provisional")
                        or duty_rate is None
                    )
                    else "clear"
                ),
                "product": primary_cargo_name,
                "origin_country": route.get(
                    "origin"
                ),
                "destination_country": route.get(
                    "destination"
                ),
                "estimated_duty_rate_percent": (
                    duty_rate
                ),
                "rate_is_provisional": bool(
                    trader.get("provisional")
                ),
                "hs_classification_status": (
                    "unconfirmed"
                    if trader.get("provisional")
                    else "reviewed"
                ),
                "fta_status": (
                    "no_known_fta"
                    if trader.get("no_known_fta")
                    else "not_confirmed"
                ),
                "summary": duty_summary,
            }
        )


    # --------------------------------------------------------
    # F. Preserve provisional duty inside landed-cost report
    # without pretending it is a final customs rate.
    # --------------------------------------------------------

    if isinstance(landed, dict):

        known_costs_sync = landed.setdefault(
            "known_inputs",
            {},
        )

        if (
            isinstance(known_costs_sync, dict)
            and duty_rate is not None
        ):

            known_costs_sync[
                "provisional_duty_rate_percent"
            ] = duty_rate

        if (
            duty_rate is not None
            and trader.get("provisional")
        ):

            landed_warnings = list(
                landed.get("warnings")
                or []
            )

            landed_warnings.append(
                "Trader Agent estimated a provisional "
                + _ux_fmt_number(duty_rate)
                + "% duty rate, but final HS "
                "classification is still required."
            )

            landed["warnings"] = _ux_unique(
                landed_warnings
            )


    # --------------------------------------------------------
    # G. Synchronize UI sections used by Reports
    # --------------------------------------------------------

    ui_sections_sync = payload.get(
        "ui_sections"
    )

    if isinstance(ui_sections_sync, list):

        for section in ui_sections_sync:

            if not isinstance(section, dict):
                continue

            section_id = section.get(
                "section_id"
            )

            metrics_sync = section.get(
                "metrics"
            )

            if not isinstance(
                metrics_sync,
                dict,
            ):
                metrics_sync = {}
                section["metrics"] = metrics_sync


            if section_id == "logistics":

                section["status"] = (
                    "review_required"
                )

                section["summary"] = (
                    "Logistics planning output is "
                    "available for first-pass review."
                )

                metrics_sync.update(
                    {
                        "total_cbm": total_cbm,
                        "total_weight_kg": (
                            total_weight
                        ),
                        "recommended_container": (
                            container_name
                        ),
                        "recommended_load_type": (
                            load_type
                        ),
                        "risk_level": risk_level,
                        "risk_score": risk_score,
                    }
                )


            elif (
                section_id
                == "compliance_documents"
            ):

                metrics_sync[
                    "required_documents"
                ] = _ux_unique(
                    required_docs
                )

                metrics_sync[
                    "conditional_documents"
                ] = _ux_unique(
                    conditional_docs
                )


            elif (
                section_id
                == "costs_insurance"
            ):

                known_ui = metrics_sync.get(
                    "known_inputs"
                )

                if not isinstance(
                    known_ui,
                    dict,
                ):
                    known_ui = {}
                    metrics_sync[
                        "known_inputs"
                    ] = known_ui

                if duty_rate is not None:

                    known_ui[
                        "provisional_duty_rate_percent"
                    ] = duty_rate

                    metrics_sync[
                        "provisional_duty_rate_percent"
                    ] = duty_rate


            elif (
                section_id
                == "partner_checks"
            ):

                partner_status = payload.get(
                    "partner_review_status"
                )

                if partner_status in (
                    None,
                    "",
                    "unknown",
                ):

                    section[
                        "status"
                    ] = "unknown"

                    section[
                        "summary"
                    ] = (
                        "No structured partner-review "
                        "result is available for this request."
                    )

                    section["bullets"] = []
                    section["actions"] = []


            elif (
                section_id
                == "executive_decision"
            ):

                bad_not_applicable = {
                    "shopping review was not applicable.",
                    "logistics review was not applicable.",
                }

                section["bullets"] = [
                    value
                    for value in (
                        section.get("bullets")
                        or []
                    )
                    if str(value).strip().lower()
                    not in bad_not_applicable
                ]


    # --------------------------------------------------------
    # H. Remove "not applicable" pseudo-risks from executive
    # summary. These are not actual shipment risks.
    # --------------------------------------------------------

    executive_sync = payload.get(
        "executive_summary"
    )

    if isinstance(executive_sync, dict):

        bad_not_applicable = {
            "shopping review was not applicable.",
            "logistics review was not applicable.",
        }

        executive_sync["top_risks"] = [
            value
            for value in (
                executive_sync.get("top_risks")
                or []
            )
            if str(value).strip().lower()
            not in bad_not_applicable
        ]


    return "\n".join(lines)


def _build_answer(payload, prompt_text, canonical):
    # FULL TRADE ANSWER V3 ROUTING
    if _full_trade_plan_requested_v2(prompt_text, payload):
        return _build_full_trade_answer_v2(
            payload,
            prompt_text,
            canonical,
        )

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
