from __future__ import annotations

import re
from typing import Any


SUPPLIER_KEYS = {
    "supplier_options",
    "suppliers",
    "shortlisted_suppliers",
    "supplier_shortlist",
    "recommended_suppliers",
}

BAD_PHRASES = [
    "shopping review has blockers",
    "no supplier items were selected",
    "resolve shopping blockers",
    "shopping has blockers",
    "no selected supplier items were found",
    "selected 0 supplier option",
    "shortlisted 0 supplier option",
    "created 0 draft purchase order",
    "do not proceed yet",
]


def _as_text(value: Any) -> str:
    return str(value or "")


def _is_bad_text(value: Any) -> bool:
    text = _as_text(value).lower()
    return any(phrase in text for phrase in BAD_PHRASES)


def _clean_bad_lists_and_text(obj: Any) -> None:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            value = obj[key]

            if isinstance(value, list):
                cleaned = []
                for item in value:
                    if isinstance(item, str) and _is_bad_text(item):
                        continue
                    cleaned.append(item)
                obj[key] = cleaned

                for child in obj[key]:
                    _clean_bad_lists_and_text(child)

            elif isinstance(value, dict):
                _clean_bad_lists_and_text(value)

            elif isinstance(value, str) and _is_bad_text(value):
                obj[key] = ""

    elif isinstance(obj, list):
        for item in obj:
            _clean_bad_lists_and_text(item)


def _deep_find(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        value = obj.get(key)
        if value not in (None, "", [], {}):
            return value

        for child in obj.values():
            found = _deep_find(child, key)
            if found not in (None, "", [], {}):
                return found

    elif isinstance(obj, list):
        for child in obj:
            found = _deep_find(child, key)
            if found not in (None, "", [], {}):
                return found

    return None


def _set_deep_known_fields(payload: dict[str, Any]) -> None:
    origin = _deep_find(payload, "origin_country") or _deep_find(payload, "origin")
    destination = _deep_find(payload, "destination_country") or _deep_find(payload, "destination")
    incoterm = _deep_find(payload, "incoterm")

    for target in [payload]:
        if origin not in (None, "", [], {}):
            target["origin"] = origin
            target["origin_country"] = origin

        if destination not in (None, "", [], {}):
            target["destination"] = destination
            target["destination_country"] = destination

        if incoterm not in (None, "", [], {}):
            target["incoterm"] = incoterm

    for nested_key in [
        "handoff_payload",
        "input_resolution",
        "shipment_input",
        "logistics_input",
        "shopping_request",
        "finance_inputs",
        "cost_inputs",
    ]:
        nested = payload.get(nested_key)
        if not isinstance(nested, dict):
            nested = {}
            payload[nested_key] = nested

        if origin not in (None, "", [], {}):
            nested["origin"] = origin
            nested["origin_country"] = origin

        if destination not in (None, "", [], {}):
            nested["destination"] = destination
            nested["destination_country"] = destination

        if incoterm not in (None, "", [], {}):
            nested["incoterm"] = incoterm


def _collect_supplier_lists(obj: Any) -> list[list[dict[str, Any]]]:
    lists: list[list[dict[str, Any]]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in SUPPLIER_KEYS and isinstance(child, list):
                    dict_items = [item for item in child if isinstance(item, dict)]
                    if dict_items:
                        lists.append(dict_items)

                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return lists


def _supplier_name(supplier: dict[str, Any], index: int) -> str:
    return _as_text(
        supplier.get("supplier_name")
        or supplier.get("name")
        or supplier.get("supplier")
        or f"Supplier candidate {index}"
    )


def _supplier_type(supplier: dict[str, Any]) -> str:
    return _as_text(
        supplier.get("supplier_type")
        or supplier.get("selection_status")
        or "shortlisted_for_review"
    )


def _supplier_note(supplier: dict[str, Any]) -> str:
    return _as_text(
        supplier.get("notes")
        or supplier.get("reason")
        or supplier.get("summary")
        or "Review price, lead time, payment terms, packing quality, certifications, and reliability before purchase order approval."
    )


def _supplier_product(supplier: dict[str, Any]) -> str:
    return _as_text(
        supplier.get("product")
        or supplier.get("product_name")
        or supplier.get("item_name")
        or ""
    ).strip()


def _supplier_options(payload: dict[str, Any]) -> list[dict[str, Any]]:
    direct = payload.get("supplier_options")
    lists = []

    if isinstance(direct, list) and direct:
        lists.append([item for item in direct if isinstance(item, dict)])

    lists.extend(_collect_supplier_lists(payload))

    unique: list[dict[str, Any]] = []
    seen = set()

    for supplier_list in lists:
        for supplier in supplier_list:
            name = _supplier_name(supplier, len(unique) + 1)
            product = _supplier_product(supplier)
            key = (name.lower(), product.lower())

            if key in seen:
                continue

            seen.add(key)
            unique.append(supplier)

    return unique


def _extract_products_from_prompt(prompt: str) -> list[str]:
    raw = _as_text(prompt)

    match = re.search(
        r"\bfind\s+suppliers\s+for\s+(.+?)(?=\s+and\s+make|\s+and\s+create|\s+from\s+|\s+to\s+|\s+using\s+|\.|$)",
        raw,
        flags=re.IGNORECASE,
    )

    if not match:
        return []

    text = match.group(1).strip(" .,:;")
    text = re.sub(r"\b\d+\s*", "", text)
    text = re.sub(
        r"\b(?:units?|pcs|pieces|cartons?|boxes?|pallets?)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    products = []

    for part in re.split(r"\s*,\s*|\s+and\s+", text):
        product = part.strip(" .,:;")
        if product:
            products.append(product)

    return products


def _products(payload: dict[str, Any], prompt: str, suppliers: list[dict[str, Any]]) -> list[str]:
    products: list[str] = []

    for supplier in suppliers:
        product = _supplier_product(supplier)
        if product:
            products.append(product)

    shopping_plan = payload.get("shopping_plan")
    if isinstance(shopping_plan, dict):
        plan_products = shopping_plan.get("products")
        if isinstance(plan_products, list):
            for product in plan_products:
                if isinstance(product, str) and product.strip():
                    products.append(product.strip())

    products.extend(_extract_products_from_prompt(prompt))

    unique = []
    seen = set()

    for product in products:
        key = product.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(product)

    return unique or ["requested product"]


def _has_quantity(prompt: str) -> bool:
    return bool(
        re.search(
            r"\b\d+\s+(?:[A-Za-z-]+\s+){0,5}(?:tiles?|bottles?|pillows?|mattresses?|units?|pcs|pieces|cartons?|boxes?|pallets?)\b",
            prompt,
            flags=re.IGNORECASE,
        )
    )


def _has_budget(prompt: str, payload: dict[str, Any]) -> bool:
    if re.search(r"\bbudget\s*(?:is|of|:)?\s*\$?\s*[0-9]", prompt, flags=re.IGNORECASE):
        return True

    value = _deep_find(payload, "budget_usd")
    return value not in (None, "", [], {}, 0, 0.0)


def _has_cost_inputs(payload: dict[str, Any]) -> bool:
    fields = [
        "freight_quote_usd",
        "insurance_premium_usd",
        "duty_rate_percent",
        "import_tax_rate_percent",
        "customs_brokerage_usd",
        "local_delivery_usd",
    ]

    return all(_deep_find(payload, field) not in (None, "", [], {}) for field in fields)


def _has_cbm_and_weight(payload: dict[str, Any]) -> bool:
    metrics = payload.get("logistics_metrics")

    if not isinstance(metrics, dict):
        return False

    return (
        metrics.get("total_cbm") not in (None, "", [], {})
        and metrics.get("total_weight_kg") not in (None, "", [], {})
    )


def _remaining_questions(payload: dict[str, Any], prompt: str) -> list[str]:
    questions = []

    if _deep_find(payload, "origin_country") in (None, "", [], {}) and _deep_find(payload, "origin") in (None, "", [], {}):
        questions.append("Origin country or supplier country")

    if _deep_find(payload, "destination_country") in (None, "", [], {}) and _deep_find(payload, "destination") in (None, "", [], {}):
        questions.append("Destination country")

    if not _has_quantity(prompt):
        questions.append("Quantity or target order volume")

    if not _has_budget(prompt, payload):
        questions.append("Budget or target unit price")

    needs_shipping = any(token in prompt.lower() for token in ["shipping plan", "ship", "shipment", "landed cost", "booking"])

    if needs_shipping and not _has_cost_inputs(payload):
        questions.append("Freight quote, insurance premium, duty rate, import tax/VAT, customs brokerage, and local delivery cost")

    if needs_shipping and not _has_cbm_and_weight(payload):
        questions.append("Final packed dimensions/CBM and total weight, if known")

    unique = []
    seen = set()

    for question in questions:
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(question)

    return unique


def _supplier_bullets(suppliers: list[dict[str, Any]]) -> list[str]:
    bullets = []

    for index, supplier in enumerate(suppliers[:6], start=1):
        bullets.append(f"{_supplier_name(supplier, index)} ({_supplier_type(supplier)}): {_supplier_note(supplier)}")

    return bullets


def _build_answer(payload: dict[str, Any], prompt: str, suppliers: list[dict[str, Any]], questions: list[str]) -> str:
    origin = _deep_find(payload, "origin_country") or _deep_find(payload, "origin") or "not confirmed"
    destination = _deep_find(payload, "destination_country") or _deep_find(payload, "destination") or "not confirmed"
    incoterm = _deep_find(payload, "incoterm") or "not confirmed"
    products = _products(payload, prompt, suppliers)

    lines = []
    lines.append("I created a first-pass supplier and shipping plan.")
    lines.append("")
    lines.append("Route and terms:")
    lines.append(f"- Origin / supplier country: {origin}")
    lines.append(f"- Destination: {destination}")
    lines.append(f"- Incoterm: {incoterm}")
    lines.append("")
    lines.append("Products:")
    for product in products:
        lines.append(f"- {product}")

    lines.append("")
    lines.append("Supplier shortlist for review:")
    for bullet in _supplier_bullets(suppliers):
        lines.append(f"- {bullet}")

    if questions:
        lines.append("")
        lines.append("Answer these details together so I can move this closer to booking readiness:")
        for question in questions:
            lines.append(f"- {question}")

    lines.append("")
    lines.append("These are first-pass planning options, not verified live supplier records. Verify supplier identity, price, lead time, certifications, packing standards, and payment terms before issuing a purchase order.")

    return "\n".join(lines)


def _set_answer_fields(payload: dict[str, Any], answer: str) -> None:
    for key in [
        "answer",
        "final_answer",
        "user_facing_answer",
        "report",
        "display_answer",
        "frontend_answer",
        "assistant_answer",
        "response_text",
        "summary",
        "short_answer",
    ]:
        payload[key] = answer


def _sync_supplier_fields(payload: dict[str, Any], suppliers: list[dict[str, Any]], products: list[str]) -> None:
    payload["supplier_options"] = suppliers
    payload["shortlisted_suppliers"] = suppliers
    payload["recommended_suppliers"] = suppliers

    shopping_plan = payload.get("shopping_plan")
    if not isinstance(shopping_plan, dict):
        shopping_plan = {}
        payload["shopping_plan"] = shopping_plan

    shopping_plan["supplier_options"] = suppliers
    shopping_plan["shortlisted_suppliers"] = suppliers
    shopping_plan["products"] = products


def _sync_procurement(payload: dict[str, Any], suppliers: list[dict[str, Any]], products: list[str], questions: list[str]) -> None:
    procurement = payload.get("procurement_advice")
    if not isinstance(procurement, dict):
        procurement = {}
        payload["procurement_advice"] = procurement

    procurement.update(
        {
            "applicable": True,
            "status": "review_required",
            "summary": "Procurement advice is usable for first-pass supplier planning.",
            "selected_items_count": max(1, len(products)),
            "supplier_options_count": len(suppliers),
            "selected_product_names": products,
            "warnings": [],
            "user_questions": questions,
        }
    )

    supplier_lines = [f"Shortlist: {bullet}" for bullet in _supplier_bullets(suppliers)]

    procurement["recommendations"] = supplier_lines + [
        "Keep shortlisted suppliers as backups before issuing final purchase orders.",
        "Request proforma invoices from shortlisted suppliers.",
        "Confirm payment terms, production lead time, warranty, packaging standard, certifications, and replacement policy.",
    ]

    procurement["negotiation_points"] = [
        "Request a proforma invoice from each shortlisted supplier.",
        "Confirm whether quoted price fits the user's budget.",
        "Confirm payment terms, production lead time, warranty, and return/replacement policy.",
        "Confirm packaging standard, export carton strength, and labeling requirements.",
    ]


def _sync_shopping_quality(payload: dict[str, Any], suppliers: list[dict[str, Any]]) -> None:
    review = payload.get("shopping_quality_review")
    if not isinstance(review, dict):
        review = {}
        payload["shopping_quality_review"] = review

    review.update(
        {
            "applicable": True,
            "status": "review_required",
            "summary": "Supplier shortlist is available for first-pass procurement planning.",
            "selected_items_count": 1,
            "supplier_options_count": len(suppliers),
            "blockers": [],
            "warnings": [],
            "recommendations": [
                "Review supplier price, lead time, packaging, certifications, payment terms, and reliability before purchase order approval."
            ],
        }
    )


def _sync_logistics(payload: dict[str, Any]) -> None:
    metrics = payload.get("logistics_metrics")

    if not isinstance(metrics, dict):
        return

    review = payload.get("logistics_quality_review")
    if not isinstance(review, dict):
        review = {}
        payload["logistics_quality_review"] = review

    for key in [
        "total_cbm",
        "total_weight_kg",
        "recommended_container",
        "recommended_load_type",
        "risk_level",
        "risk_score",
        "readiness_status",
    ]:
        if key in metrics:
            review[key] = metrics.get(key)

    review["applicable"] = True
    review["status"] = "review_required"
    review["summary"] = "Logistics plan is usable for first-pass planning but needs review before booking."

    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict):
        container = visualizer.get("container")
        if isinstance(container, dict):
            if metrics.get("recommended_container") not in (None, "", [], {}):
                container["selected_container"] = metrics.get("recommended_container")
            if metrics.get("recommended_load_type") not in (None, "", [], {}):
                container["recommended_load_type"] = metrics.get("recommended_load_type")
            if metrics.get("total_cbm") not in (None, "", [], {}):
                container["total_cbm"] = metrics.get("total_cbm")
            if metrics.get("total_weight_kg") not in (None, "", [], {}):
                container["total_weight_kg"] = metrics.get("total_weight_kg")


def _sync_agent_summaries(payload: dict[str, Any], suppliers: list[dict[str, Any]]) -> None:
    metrics = payload.get("logistics_metrics")
    if not isinstance(metrics, dict):
        metrics = {}

    summaries = payload.get("agent_summaries")
    if not isinstance(summaries, list):
        summaries = []

    new_summaries = []

    supplier_names = ", ".join(_supplier_name(supplier, index) for index, supplier in enumerate(suppliers[:3], start=1))

    new_summaries.append(
        {
            "agent_name": "shopping_agent",
            "status": "review_required",
            "summary": f"Shopping Agent status: review_required. Shortlisted {len(suppliers)} supplier option(s): {supplier_names}.",
        }
    )

    if metrics.get("total_cbm") not in (None, "", [], {}) or metrics.get("total_weight_kg") not in (None, "", [], {}):
        new_summaries.append(
            {
                "agent_name": "logistics_agent",
                "status": "review_required",
                "summary": f"Logistics plan status: review_required. Total cargo is {metrics.get('total_cbm')} CBM and {metrics.get('total_weight_kg')} kg. Recommended container: {metrics.get('recommended_container')}.",
            }
        )

    for item in summaries:
        if not isinstance(item, dict):
            continue

        if item.get("agent_name") in {"shopping_agent", "logistics_agent"}:
            continue

        _clean_bad_lists_and_text(item)
        new_summaries.append(item)

    payload["agent_summaries"] = new_summaries


def _sync_readiness_and_actions(payload: dict[str, Any], questions: list[str], suppliers: list[dict[str, Any]]) -> None:
    payload["status"] = "partial_plan_needs_more_information" if questions else "review_required"
    payload["decision"] = "needs_more_information" if questions else "review_required"
    payload["blockers"] = []
    payload["clarification_questions"] = questions
    payload["missing_information_count"] = len(questions)
    payload["missing_information_preview"] = questions

    booking = payload.get("booking_readiness")
    if not isinstance(booking, dict):
        booking = {}
        payload["booking_readiness"] = booking

    booking.update(
        {
            "applicable": True,
            "status": "needs_more_information" if questions else "review_required",
            "summary": "First-pass supplier planning is ready, but booking still needs missing details." if questions else "First-pass supplier planning is ready for review.",
            "score": max(int(booking.get("score") or 0), 40),
            "ready_for_first_pass": True,
            "ready_for_booking": False,
            "next_gate": "fill_missing_information" if questions else "review_before_booking",
            "blockers": [],
            "missing_information": questions,
            "next_steps": [
                "Review shortlisted suppliers.",
                "Answer remaining missing details in one submission." if questions else "Prepare supplier review and document checks.",
                "Confirm documents and landed-cost inputs before final booking.",
            ],
        }
    )

    action = payload.get("action_plan")
    if not isinstance(action, dict):
        action = {}
        payload["action_plan"] = action

    action.update(
        {
            "status": "fill_missing_information" if questions else "review_supplier_shortlist",
            "summary": "A supplier shortlist is available; answer remaining questions together to continue.",
            "immediate_actions": [
                "Review the supplier shortlist.",
                "Answer the missing details in one submission." if questions else "Proceed to supplier review.",
            ],
            "before_booking": [
                "Confirm supplier identity and proforma invoice.",
                "Confirm price, lead time, payment terms, packaging, certifications, and warranty.",
                "Confirm freight, insurance, duty, VAT/import tax, customs brokerage, and local delivery cost before final landed cost.",
            ],
            "user_questions": questions,
            "ready_to_continue": [
                f"{len(suppliers)} supplier option(s) available for review."
            ],
        }
    )

    verdict = payload.get("final_verdict")
    if isinstance(verdict, dict):
        verdict["blockers"] = []
        verdict["missing_information_count"] = len(questions)

    executive = payload.get("executive_summary")
    if not isinstance(executive, dict):
        executive = {}
        payload["executive_summary"] = executive

    executive.update(
        {
            "applicable": True,
            "status": "needs_more_information" if questions else "review_required",
            "headline": "First-pass supplier shortlist is ready; booking needs more details." if questions else "First-pass supplier shortlist is ready for review.",
            "decision": "needs_more_information" if questions else "review_required",
            "ready_for_first_pass": True,
            "ready_for_booking": False,
            "booking_score": max(int(executive.get("booking_score") or 0), 40),
            "next_gate": "fill_missing_information" if questions else "review_before_booking",
            "top_missing_items": questions,
            "top_next_actions": action["immediate_actions"],
            "top_strengths": [
                f"{len(suppliers)} supplier option(s) are available for review."
            ],
        }
    )

    snapshot = executive.get("shipment_snapshot")
    if not isinstance(snapshot, dict):
        snapshot = {}
        executive["shipment_snapshot"] = snapshot

    metrics = payload.get("logistics_metrics")
    if isinstance(metrics, dict):
        snapshot["total_cbm"] = metrics.get("total_cbm")
        snapshot["total_weight_kg"] = metrics.get("total_weight_kg")
        snapshot["recommended_container"] = metrics.get("recommended_container")
        snapshot["recommended_load_type"] = metrics.get("recommended_load_type")
        snapshot["risk_level"] = metrics.get("risk_level")

    for key in ["origin_country", "destination_country", "incoterm"]:
        value = _deep_find(payload, key)
        if value not in (None, "", [], {}):
            snapshot[key] = value


def _sync_ui_sections(payload: dict[str, Any], suppliers: list[dict[str, Any]], questions: list[str], answer: str) -> None:
    supplier_bullets = _supplier_bullets(suppliers)

    answer_section = {
        "section_id": "answer",
        "title": "Answer",
        "status": "needs_more_information" if questions else "review_required",
        "summary": answer,
        "bullets": supplier_bullets,
        "actions": questions,
    }

    supplier_section = {
        "section_id": "supplier_shortlist",
        "title": "Supplier Shortlist",
        "status": "review_required",
        "summary": "First-pass supplier options generated for review.",
        "bullets": supplier_bullets,
        "actions": [
            "Confirm supplier identity, proforma invoice, price, lead time, packaging, certifications, and payment terms."
        ],
    }

    old_sections = payload.get("ui_sections")
    keep = []

    if isinstance(old_sections, list):
        for section in old_sections:
            if not isinstance(section, dict):
                continue
            if section.get("section_id") in {"answer", "supplier_shortlist"}:
                continue
            _clean_bad_lists_and_text(section)
            keep.append(section)

    payload["ui_sections"] = [answer_section, supplier_section] + keep


def sync_shopping_frontend_payload(payload: Any, prompt: Any = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = _as_text(prompt)

    detected = _as_text(payload.get("detected_intent") or payload.get("intent")).lower()
    agents = payload.get("agents_called") or []

    is_shopping = (
        "shopping" in detected
        or "shopping_agent" in agents
        or "find suppliers" in text.lower()
        or "supplier" in text.lower()
    )

    if not is_shopping:
        return payload

    _clean_bad_lists_and_text(payload)
    _set_deep_known_fields(payload)

    suppliers = _supplier_options(payload)
    if not suppliers:
        return payload

    products = _products(payload, text, suppliers)
    questions = _remaining_questions(payload, text)
    answer = _build_answer(payload, text, suppliers, questions)

    _sync_supplier_fields(payload, suppliers, products)
    _sync_procurement(payload, suppliers, products, questions)
    _sync_shopping_quality(payload, suppliers)
    _sync_logistics(payload)
    _sync_agent_summaries(payload, suppliers)
    _sync_readiness_and_actions(payload, questions, suppliers)
    _sync_ui_sections(payload, suppliers, questions, answer)
    _set_answer_fields(payload, answer)

    payload["shopping_frontend_synced"] = True
    payload["shopping_frontend_sync_version"] = "v2"

    return payload
