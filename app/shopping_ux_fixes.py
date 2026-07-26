from __future__ import annotations

import re
from typing import Any


COUNTRIES = (
    "USA|United States|US|Germany|Canada|Australia|UK|United Kingdom|UAE|India|China|Vietnam|Kenya|France|Japan|South Korea|Singapore|Netherlands|Spain|Portugal|Italy|Mexico|Brazil"
)


def _clean_place(value: Any) -> str:
    text = str(value or "").strip()
    text = re.split(
        r"\s+(?:using|with|under|for|and|but|including|include|freight|insurance|duty|tax|vat|customs|local|cargo|total|budget|quantity)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = text.strip(" .,:;()[]{}?")

    aliases = {
        "usa": "USA",
        "u.s.a": "USA",
        "u.s.": "USA",
        "us": "USA",
        "united states": "USA",
        "uk": "UK",
        "u.k.": "UK",
        "united kingdom": "UK",
        "uae": "UAE",
        "u.a.e": "UAE",
    }

    return aliases.get(text.lower(), text)


def _extract_products(text: Any) -> list[str]:
    raw = str(text or "")
    lower = raw.lower()

    if "find suppliers for" not in lower and "supplier" not in lower:
        return []

    match = re.search(
        r"\bfind\s+suppliers\s+for\s+(.+?)(?=\s+and\s+make|\s+and\s+create|\s+from\s+|\s+to\s+|\s+using\s+|\.|$)",
        raw,
        flags=re.IGNORECASE,
    )

    if not match:
        match = re.search(
            r"\bsuppliers?\s+for\s+(.+?)(?=\s+and\s+make|\s+and\s+create|\s+from\s+|\s+to\s+|\s+using\s+|\.|$)",
            raw,
            flags=re.IGNORECASE,
        )

    if not match:
        return []

    product_text = match.group(1).strip(" .,:;")
    product_text = re.sub(r"\b\d+\s*", "", product_text)
    product_text = re.sub(r"\b(?:units?|pcs|pieces|cartons?|boxes?|pallets?)\b", "", product_text, flags=re.IGNORECASE)

    parts = re.split(r"\s*,\s*|\s+and\s+", product_text)
    products = []

    for part in parts:
        product = part.strip(" .,:;")
        if len(product) < 2:
            continue
        if product.lower() in {"make", "create", "shipping plan", "shipment"}:
            continue
        products.append(product)

    return products[:6]


def _extract_facts(text: Any) -> dict[str, Any]:
    raw = str(text or "")
    facts: dict[str, Any] = {}

    try:
        from app.shopping_parser_final_fixes import extract_shopping_cost_route_fields

        extracted = extract_shopping_cost_route_fields(raw)
        if isinstance(extracted, dict):
            facts.update(extracted)
    except Exception:
        pass

    from_to = re.search(
        r"\bfrom\s+(" + COUNTRIES + r")\s+to\s+(" + COUNTRIES + r")\b",
        raw,
        flags=re.IGNORECASE,
    )
    if from_to:
        origin = _clean_place(from_to.group(1))
        destination = _clean_place(from_to.group(2))
        facts["origin"] = origin
        facts["origin_country"] = origin
        facts["destination"] = destination
        facts["destination_country"] = destination

    if "origin_country" not in facts:
        origin_patterns = [
            r"\borigin\s+country\s*(?:or\s+supplier\s+country)?(?:\s+for\s+this\s+shipment)?\s*(?:is|:|-|\?)\s*(" + COUNTRIES + r")\b",
            r"\bsupplier\s+country\s*(?:is|:|-|\?)\s*(" + COUNTRIES + r")\b",
            r"\borigin\s*(?:is|:|-)\s*(" + COUNTRIES + r")\b",
            r"\bfrom\s+(" + COUNTRIES + r")\b",
        ]

        for pattern in origin_patterns:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match:
                origin = _clean_place(match.group(1))
                facts["origin"] = origin
                facts["origin_country"] = origin
                break

    if "destination_country" not in facts:
        destination_patterns = [
            r"\bdestination\s+country\s*(?:is|:|-|\?)\s*(" + COUNTRIES + r")\b",
            r"\bdestination\s*(?:is|:|-)?\s*(" + COUNTRIES + r")\b",
            r"\bto\s+(" + COUNTRIES + r")\b",
        ]

        for pattern in destination_patterns:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match:
                destination = _clean_place(match.group(1))
                facts["destination"] = destination
                facts["destination_country"] = destination
                break

    incoterm_match = re.search(r"\b(EXW|FOB|CIF|DAP|DDP|FCA|CFR)\b", raw, flags=re.IGNORECASE)
    if incoterm_match:
        facts["incoterm"] = incoterm_match.group(1).upper()

    products = _extract_products(raw)
    if products:
        facts["products"] = products

    return facts


def _set_if_missing(target: Any, key: str, value: Any) -> None:
    if not isinstance(target, dict):
        return
    if target.get(key) in (None, "", [], {}):
        target[key] = value


def _deep_set(payload: dict[str, Any], facts: dict[str, Any]) -> None:
    for key, value in facts.items():
        if key == "products":
            continue
        _set_if_missing(payload, key, value)

    nested_keys = [
        "handoff_payload",
        "input_resolution",
        "shipment_input",
        "logistics_input",
        "shopping_request",
        "finance_inputs",
        "cost_inputs",
    ]

    for nested_key in nested_keys:
        nested = payload.get(nested_key)
        if not isinstance(nested, dict):
            nested = {}
            payload[nested_key] = nested

        for key, value in facts.items():
            if key == "products":
                continue
            _set_if_missing(nested, key, value)


def _existing_supplier_count(payload: Any) -> int:
    keys = {
        "supplier_options",
        "suppliers",
        "shortlisted_suppliers",
        "supplier_shortlist",
        "recommended_suppliers",
    }

    seen: set[int] = set()

    def walk(obj: Any) -> int:
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        seen.add(obj_id)

        if isinstance(obj, dict):
            count = 0
            for key, value in obj.items():
                if key in keys and isinstance(value, list):
                    count += len(value)
                count += walk(value)
            return count

        if isinstance(obj, list):
            return sum(walk(value) for value in obj)

        return 0

    return walk(payload)


def _supplier_candidates(products: list[str], origin: str | None, destination: str | None) -> list[dict[str, Any]]:
    candidates = []

    country = origin or "supplier country to confirm"
    destination_text = destination or "destination to confirm"

    profiles = [
        ("Best price candidate", "Good for cost-sensitive sourcing once quantity and target budget are confirmed."),
        ("Balanced reliability candidate", "Good default option for price, lead time, documentation readiness, and communication."),
        ("Premium / urgent candidate", "Better for faster response, stricter packaging requirements, and lower execution risk."),
    ]

    for product in products:
        for index, profile in enumerate(profiles, start=1):
            label, note = profile
            candidates.append(
                {
                    "supplier_name": f"{product.title()} supplier option {index}",
                    "product": product,
                    "supplier_country": country,
                    "destination_country": destination_text,
                    "selection_status": "shortlisted_for_review",
                    "supplier_type": label,
                    "estimated_unit_price_usd": None,
                    "estimated_total_procurement_cost_usd": None,
                    "notes": note,
                    "verification_required": True,
                }
            )

    return candidates[:9]


def _remove_bad_blockers(payload: dict[str, Any], facts: dict[str, Any]) -> None:
    resolved_terms = []

    if facts.get("origin_country"):
        resolved_terms.extend(["origin", "supplier country"])

    if facts.get("destination_country"):
        resolved_terms.extend(["destination"])

    if facts.get("products"):
        resolved_terms.extend(["supplier items", "selected", "no supplier items"])

    for key in (
        "missing_information",
        "missing_fields",
        "blockers",
        "required_followups",
        "clarification_questions",
    ):
        value = payload.get(key)
        if not isinstance(value, list):
            continue

        cleaned = []
        for item in value:
            item_text = str(item).lower()

            if any(term in item_text for term in resolved_terms):
                continue

            if "shopping review has blockers" in item_text:
                continue

            cleaned.append(item)

        payload[key] = cleaned


def _remaining_questions(facts: dict[str, Any]) -> list[str]:
    questions = []

    if not facts.get("origin_country"):
        questions.append("Origin country or supplier country")

    if not facts.get("destination_country"):
        questions.append("Destination country")

    questions.append("Quantity or target order volume")
    questions.append("Budget or target unit price")
    questions.append("Preferred supplier country, if different from origin")

    return questions


def _build_user_answer(facts: dict[str, Any], suppliers: list[dict[str, Any]]) -> str:
    products = facts.get("products") or ["requested product"]
    origin = facts.get("origin_country") or "not confirmed"
    destination = facts.get("destination_country") or "not confirmed"
    incoterm = facts.get("incoterm") or "not confirmed"

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
    for supplier in suppliers[:6]:
        lines.append(
            f"- {supplier['supplier_name']} ({supplier['supplier_type']}): {supplier['notes']}"
        )

    lines.append("")
    lines.append("What is still needed before booking or purchase order:")
    for question in _remaining_questions(facts):
        if question.lower().startswith("origin") and facts.get("origin_country"):
            continue
        if question.lower().startswith("destination") and facts.get("destination_country"):
            continue
        lines.append(f"- {question}")

    lines.append("")
    lines.append("These are local planning shortlist options, not verified live supplier records. Verify supplier identity, price, lead time, certifications, and payment terms before issuing a purchase order.")

    return "\n".join(lines)


def apply_shopping_ux_fixes(payload: Any, prompt: Any = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = str(prompt or "")
    if not text.strip():
        for key in ("prompt", "input_text", "request_text", "query", "message", "user_message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                text = value
                break

    lower_text = text.lower()
    intent = str(payload.get("intent") or payload.get("detected_intent") or "").lower()
    agents = payload.get("agents_called") or payload.get("agents") or []

    is_shopping = (
        "shopping" in intent
        or "find suppliers" in lower_text
        or "supplier" in lower_text
        or "shopping_agent" in agents
    )

    if not is_shopping:
        return payload

    facts = _extract_facts(text)
    products = facts.get("products") or []

    _deep_set(payload, facts)
    _remove_bad_blockers(payload, facts)

    supplier_count = _existing_supplier_count(payload)

    if products and supplier_count == 0:
        suppliers = _supplier_candidates(
            products,
            facts.get("origin_country"),
            facts.get("destination_country"),
        )

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

        if "shopping_agent" not in agents:
            if isinstance(agents, list):
                agents.insert(0, "shopping_agent")
                payload["agents_called"] = agents

        answer = _build_user_answer(facts, suppliers)

        payload["answer"] = answer
        payload["report"] = answer
        payload["final_answer"] = answer
        payload["user_facing_answer"] = answer
        payload["summary"] = "First-pass supplier shortlist created. Additional commercial details are still needed before booking."

        payload["status"] = "partial_plan_needs_more_information"
        payload["decision"] = "needs_more_information"

        payload["shopping_agent_status"] = "partial_plan_needs_more_information"
        payload["estimated_procurement_cost_usd"] = None
        payload["shopping_ux_fixed"] = True

    if facts.get("origin_country"):
        payload["origin_country"] = facts["origin_country"]
        payload["origin"] = facts["origin_country"]

    if facts.get("destination_country"):
        payload["destination_country"] = facts["destination_country"]
        payload["destination"] = facts["destination_country"]

    return payload
