from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any

REFERENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "dynamic_compliance_reference_v65.json"
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()

    for value in values:
        if value in (None, "", [], {}):
            continue

        marker = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ).lower()

        if marker in seen:
            continue

        seen.add(marker)
        result.append(value)

    return result


def _add_unique(target: list[Any], *values: Any) -> None:
    target[:] = _unique([*target, *values])


def _request_text(payload: dict[str, Any], original_text: str | None) -> str:
    if isinstance(original_text, str) and original_text.strip():
        return original_text.strip()

    metadata = _as_dict(payload.get("request_metadata"))

    for key in (
        "input_source",
        "original_text",
        "user_text",
        "prompt",
        "request_text",
    ):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for key in (
        "original_text",
        "user_text",
        "prompt",
        "request_text",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _normalise_country(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = re.sub(r"\s+", " ", value).strip(" \t\r\n,.;:")
    lowered = cleaned.lower()

    aliases = {
        "uae": "UAE",
        "u.a.e": "UAE",
        "united arab emirates": "UAE",
        "the united arab emirates": "UAE",
        "israel": "Israel",
        "haifa": "Israel",
        "iran": "Iran",
        "islamic republic of iran": "Iran",
        "china": "China",
        "germany": "Germany",
        "hamburg": "Germany",
        "france": "France",
        "usa": "USA",
        "u.s.a": "USA",
        "us": "USA",
        "u.s": "USA",
        "united states": "USA",
        "the united states": "USA",
        "united states of america": "USA",
    }

    return aliases.get(lowered, cleaned or None)


def _countries(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    sections = [
        _as_dict(payload.get("trade_agreement_advice")),
        _as_dict(payload.get("trade_compliance_readiness")),
        _as_dict(payload.get("route_plan")),
        _as_dict(payload.get("trade_terms_advice")),
        payload,
    ]

    origin = None
    destination = None

    for section in sections:
        if not origin:
            for key in ("origin_country", "origin", "country_from"):
                origin = _normalise_country(section.get(key))
                if origin:
                    break

        if not destination:
            for key in (
                "destination_country",
                "destination",
                "country_to",
            ):
                destination = _normalise_country(section.get(key))
                if destination:
                    break

    return origin, destination


def _pair_key(origin: str | None, destination: str | None) -> str:
    values = sorted(
        value.lower()
        for value in (origin, destination)
        if isinstance(value, str) and value
    )
    return "|".join(values)


def _load_reference() -> dict[str, Any]:
    try:
        value = json.loads(
            REFERENCE_PATH.read_text(
                encoding="utf-8-sig",
            )
        )
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _text_without_negations(text: str) -> str:
    lowered = text.lower()

    patterns = [
        r"\bnon[-\s]?hazardous\b",
        r"\bnot\s+hazardous\b",
        r"\bdoes\s+not\s+contain\s+hazardous\s+materials?\b",
        r"\bno\s+hazardous\s+materials?\b",
        r"\bnot\s+fragile\b",
        r"\bnon[-\s]?fragile\b",
        r"\bnot\s+radioactive\b",
        r"\bnot\s+dangerous\s+goods?\b",
    ]

    for pattern in patterns:
        lowered = re.sub(pattern, " ", lowered)

    return lowered


def _cargo_signals(payload: dict[str, Any], text: str) -> dict[str, bool]:
    lowered = text.lower()
    positive_text = _text_without_negations(text)

    explicit_non_hazardous = bool(
        re.search(
            r"\b(?:non[-\s]?hazardous|not\s+hazardous|"
            r"does\s+not\s+contain\s+hazardous|no\s+hazardous)\b",
            lowered,
        )
    )
    explicit_not_fragile = bool(
        re.search(
            r"\b(?:not\s+fragile|non[-\s]?fragile)\b",
            lowered,
        )
    )
    explicit_stackable = bool(
        re.search(r"\bstackable\b", lowered)
        and not re.search(
            r"\b(?:non[-\s]?stackable|not\s+stackable)\b",
            lowered,
        )
    )

    positive_hazardous = bool(
        re.search(
            r"\b(?:hazardous\s+cargo|dangerous\s+goods?|"
            r"lithium(?:[-\s]?ion)?\s+batter(?:y|ies)|"
            r"radioactive|class\s*7|flammable|explosive|"
            r"corrosive|toxic)\b",
            positive_text,
        )
    )
    positive_fragile = bool(
        re.search(r"\bfragile\b", positive_text)
    )
    positive_non_stackable = bool(
        re.search(
            r"\b(?:non[-\s]?stackable|not\s+stackable|do\s+not\s+stack)\b",
            lowered,
        )
    )

    visual_items = _as_list(
        _as_dict(payload.get("logistics_visualizer")).get(
            "cargo_mix"
        )
    )

    visual_hazardous = any(
        bool(_as_dict(item).get("hazardous"))
        for item in visual_items
    )
    visual_fragile = any(
        bool(_as_dict(item).get("fragile"))
        for item in visual_items
    )
    visual_non_stackable = any(
        _as_dict(item).get("stackable") is False
        for item in visual_items
    )

    hazardous = positive_hazardous or (
        visual_hazardous and not explicit_non_hazardous
    )
    fragile = positive_fragile or (
        visual_fragile and not explicit_not_fragile
    )
    non_stackable = positive_non_stackable or (
        visual_non_stackable and not explicit_stackable
    )

    return {
        "hazardous": hazardous,
        "fragile": fragile,
        "non_stackable": non_stackable,
        "explicit_non_hazardous": explicit_non_hazardous,
        "explicit_not_fragile": explicit_not_fragile,
        "explicit_stackable": explicit_stackable,
    }


def _line_conflicts(
    value: Any,
    signals: dict[str, bool],
) -> bool:
    text = str(value).lower()

    if not signals["hazardous"] and any(
        term in text
        for term in (
            "hazardous",
            "dangerous goods",
            "dangerous-goods",
            "radioactive",
            "sds",
            "msds",
            "un number",
            "packing group",
        )
    ):
        return True

    if not signals["fragile"] and any(
        term in text
        for term in (
            "fragile",
            "cushioning",
        )
    ):
        return True

    if not signals["non_stackable"] and any(
        term in text
        for term in (
            "non-stackable",
            "non stackable",
            "do not stack",
            "reserve floor space",
        )
    ):
        return True

    return False


def _filter_lines(
    values: Any,
    signals: dict[str, bool],
) -> list[Any]:
    return [
        value
        for value in _as_list(values)
        if not _line_conflicts(value, signals)
    ]


def _clean_nested_lists(
    value: Any,
    signals: dict[str, bool],
) -> None:
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if isinstance(child, list) and key in {
                "blockers",
                "warnings",
                "recommendations",
                "reasons",
                "review_items",
                "immediate_actions",
                "before_booking",
                "top_risks",
                "top_next_actions",
                "bullets",
                "actions",
                "compliance_flags",
            }:
                value[key] = _filter_lines(child, signals)
            else:
                _clean_nested_lists(child, signals)

    elif isinstance(value, list):
        for child in value:
            _clean_nested_lists(child, signals)


def _actual_categories(
    payload: dict[str, Any],
    signals: dict[str, bool],
) -> list[str]:
    categories: list[str] = []

    visual_items = _as_list(
        _as_dict(payload.get("logistics_visualizer")).get(
            "cargo_mix"
        )
    )

    for item in visual_items:
        section = _as_dict(item)
        for tag in _as_list(section.get("category_tags")):
            categories.append(str(tag))

    lowered = {
        str(category).lower().replace("-", "_").replace(" ", "_")
        for category in categories
    }

    if not signals["hazardous"]:
        lowered.discard("hazardous")
        lowered.discard("radioactive")
    if not signals["fragile"]:
        lowered.discard("fragile")
    if not signals["non_stackable"]:
        lowered.discard("non_stackable")

    if signals["hazardous"]:
        lowered.add("hazardous")
    if signals["fragile"]:
        lowered.add("fragile")
    if signals["non_stackable"]:
        lowered.add("non_stackable")

    return sorted(lowered)


def _remove_false_positive_cargo_mixups(
    payload: dict[str, Any],
    signals: dict[str, bool],
) -> None:
    _clean_nested_lists(payload, signals)

    metrics = _as_dict(payload.get("logistics_metrics"))
    categories = _actual_categories(payload, signals)

    logistics = _as_dict(payload.get("logistics_quality_review"))
    if logistics:
        logistics["cargo_categories"] = categories
        logistics["risk_level"] = (
            metrics.get("risk_level")
            or logistics.get("risk_level")
        )
        logistics["risk_score"] = (
            metrics.get("risk_score")
            if metrics.get("risk_score") is not None
            else logistics.get("risk_score")
        )
        logistics["blockers"] = _filter_lines(
            logistics.get("blockers"),
            signals,
        )
        logistics["warnings"] = _filter_lines(
            logistics.get("warnings"),
            signals,
        )
        logistics["recommendations"] = _filter_lines(
            logistics.get("recommendations"),
            signals,
        )

        if not logistics.get("blockers"):
            logistics["status"] = "review_required"
            logistics["summary"] = (
                "Logistics plan is usable for first-pass planning "
                "but still requires normal booking review."
            )

    insurance = _as_dict(payload.get("insurance_advice"))
    if insurance:
        insurance["cargo_categories"] = categories
        insurance["risk_level"] = (
            metrics.get("risk_level")
            or insurance.get("risk_level")
        )
        insurance["risk_score"] = (
            metrics.get("risk_score")
            if metrics.get("risk_score") is not None
            else insurance.get("risk_score")
        )
        insurance["blockers"] = _filter_lines(
            insurance.get("blockers"),
            signals,
        )
        insurance["warnings"] = _filter_lines(
            insurance.get("warnings"),
            signals,
        )
        insurance["recommendations"] = _filter_lines(
            insurance.get("recommendations"),
            signals,
        )

        if not insurance.get("blockers"):
            insurance["status"] = "review_required"
            insurance["insurance_recommendation"] = (
                "strongly_recommended"
            )
            insurance["summary"] = (
                "Cargo insurance should be reviewed before booking."
            )

    if not any(
        (
            signals["hazardous"],
            signals["fragile"],
            signals["non_stackable"],
        )
    ):
        if payload.get("status") == "critical_review_required":
            payload["status"] = "review_required"

        final_verdict = _as_dict(payload.get("final_verdict"))
        statuses = _as_list(
            final_verdict.get("agent_statuses")
        )
        final_verdict["agent_statuses"] = [
            (
                "ready_for_review"
                if status == "critical_review_required"
                else status
            )
            for status in statuses
        ]

        summaries = _as_list(payload.get("agent_summaries"))
        for summary in summaries:
            section = _as_dict(summary)
            if section.get("agent_name") == "logistics_agent":
                section["status"] = "ready_for_review"
                section["summary"] = (
                    "Logistics calculations are available for "
                    "first-pass review."
                )


def _ensure_sections(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    documents = payload.get("document_requirements_advice")
    if not isinstance(documents, dict):
        documents = {}
        payload["document_requirements_advice"] = documents

    documents.setdefault("applicable", True)
    documents.setdefault("status", "needs_more_information")
    documents.setdefault(
        "summary",
        "Document requirements need confirmation before booking.",
    )
    documents.setdefault("required_documents", [])
    documents.setdefault("conditional_documents", [])
    documents.setdefault(
        "missing_or_unconfirmed_documents",
        [],
    )
    documents.setdefault("warnings", [])
    documents.setdefault("recommendations", [])
    documents.setdefault("user_questions", [])

    compliance = payload.get("trade_compliance_readiness")
    if not isinstance(compliance, dict):
        compliance = {}
        payload["trade_compliance_readiness"] = compliance

    compliance.setdefault("applicable", True)
    compliance.setdefault("status", "review_required")
    compliance.setdefault(
        "summary",
        "Trade compliance requires review before booking.",
    )
    compliance.setdefault("blockers", [])
    compliance.setdefault("missing_information", [])
    compliance.setdefault("warnings", [])
    compliance.setdefault("compliance_flags", [])
    compliance.setdefault("recommendations", [])
    compliance.setdefault("ready_items", [])

    return documents, compliance


def _cargo_label(text: str) -> str | None:
    lowered = text.lower()

    if "drone" in lowered:
        return "commercial drones with thermal cameras"
    if "iridium-192" in lowered or "iridium 192" in lowered:
        return "Iridium-192 industrial radiography source"
    if "lithium" in lowered and "batter" in lowered:
        return "standalone lithium-ion batteries"

    return None


def _apply_agreement(
    payload: dict[str, Any],
    documents: dict[str, Any],
    origin: str | None,
    destination: str | None,
    reference: dict[str, Any],
) -> None:
    pair = _pair_key(origin, destination)
    rule = _as_dict(
        _as_dict(reference.get("agreements")).get(pair)
    )
    if not rule:
        return

    agreement = payload.get("trade_agreement_advice")
    if not isinstance(agreement, dict):
        agreement = {}
        payload["trade_agreement_advice"] = agreement

    agreement.update(
        {
            "applicable": True,
            "status": "review_required",
            "summary": rule.get("summary"),
            "origin_country": origin,
            "destination_country": destination,
            "agreement_exists_in_local_reference": True,
            "agreement_name": rule.get("agreement_name"),
            "preferential_eligibility_status": (
                "hs_and_origin_review_required"
            ),
            "preference_claim_status": (
                "not_established_until_product_review"
            ),
            "proof_of_origin_documents": deepcopy(
                rule.get("proof_of_origin_documents") or []
            ),
            "source": rule.get("source"),
            "source_status": (
                "official_static_reference_not_live_tariff"
            ),
            "official_verification_required": True,
            "warnings": deepcopy(rule.get("warnings") or []),
            "recommendations": deepcopy(
                rule.get("recommendations") or []
            ),
        }
    )

    conditional = _as_list(
        documents.get("conditional_documents")
    )
    _add_unique(
        conditional,
        *(rule.get("proof_of_origin_documents") or []),
    )
    documents["conditional_documents"] = conditional

    recommendations = _as_list(
        documents.get("recommendations")
    )
    _add_unique(
        recommendations,
        *(rule.get("recommendations") or []),
    )
    documents["recommendations"] = recommendations


def _apply_country_control(
    payload: dict[str, Any],
    documents: dict[str, Any],
    compliance: dict[str, Any],
    origin: str | None,
    destination: str | None,
    reference: dict[str, Any],
) -> bool:
    pair = _pair_key(origin, destination)
    rule = _as_dict(
        _as_dict(reference.get("country_pair_controls")).get(
            pair
        )
    )
    if not rule:
        return False

    payload["country_pair_control"] = {
        "applicable": True,
        "status": rule.get("status", "blocked"),
        "summary": rule.get("summary"),
        "origin_country": origin,
        "destination_country": destination,
        "control_type": rule.get("control_type"),
        "source_status": "static_reference_verify_officially",
        "official_verification_required": True,
    }

    compliance["status"] = "blocked"
    compliance["summary"] = rule.get("summary")
    compliance["ready_for_partner_review"] = False

    blockers = _as_list(compliance.get("blockers"))
    _add_unique(blockers, *(rule.get("blockers") or []))
    compliance["blockers"] = blockers

    flags = _as_list(compliance.get("compliance_flags"))
    _add_unique(flags, *(rule.get("flags") or []))
    compliance["compliance_flags"] = flags

    recommendations = _as_list(
        compliance.get("recommendations")
    )
    _add_unique(
        recommendations,
        *(rule.get("recommendations") or []),
    )
    compliance["recommendations"] = recommendations

    conditional = _as_list(
        documents.get("conditional_documents")
    )
    _add_unique(
        conditional,
        *(rule.get("conditional_documents") or []),
    )
    documents["conditional_documents"] = conditional

    warnings = _as_list(documents.get("warnings"))
    _add_unique(warnings, rule.get("summary"))
    documents["warnings"] = warnings

    return True


def _matched_cargo_rules(
    text: str,
    reference: dict[str, Any],
) -> list[dict[str, Any]]:
    lowered = text.lower()
    matched: list[dict[str, Any]] = []

    for rule in _as_list(reference.get("cargo_controls")):
        section = _as_dict(rule)
        terms = [
            str(value).lower()
            for value in _as_list(section.get("match_any"))
        ]

        if any(term in lowered for term in terms):
            matched.append(section)

    return matched


def _apply_cargo_controls(
    payload: dict[str, Any],
    documents: dict[str, Any],
    compliance: dict[str, Any],
    text: str,
    reference: dict[str, Any],
) -> list[str]:
    matched = _matched_cargo_rules(text, reference)
    if not matched:
        return []

    labels: list[str] = []

    for rule in matched:
        label = str(rule.get("id") or "special_control")
        labels.append(label)

        conditional = _as_list(
            documents.get("conditional_documents")
        )
        _add_unique(
            conditional,
            *(rule.get("conditional_documents") or []),
        )
        documents["conditional_documents"] = conditional

        warnings = _as_list(documents.get("warnings"))
        _add_unique(warnings, *(rule.get("warnings") or []))
        documents["warnings"] = warnings

        doc_recommendations = _as_list(
            documents.get("recommendations")
        )
        _add_unique(
            doc_recommendations,
            *(rule.get("recommendations") or []),
        )
        documents["recommendations"] = doc_recommendations

        blockers = _as_list(compliance.get("blockers"))
        _add_unique(blockers, *(rule.get("blockers") or []))
        compliance["blockers"] = blockers

        flags = _as_list(
            compliance.get("compliance_flags")
        )
        _add_unique(flags, *(rule.get("flags") or []))
        compliance["compliance_flags"] = flags

        recommendations = _as_list(
            compliance.get("recommendations")
        )
        _add_unique(
            recommendations,
            *(rule.get("recommendations") or []),
        )
        compliance["recommendations"] = recommendations

    compliance["status"] = "blocked"
    compliance["ready_for_partner_review"] = False
    compliance["summary"] = (
        "Trade compliance is blocked pending product-control "
        "classification, required licences, and official approvals."
    )

    label = _cargo_label(text)
    if label:
        documents["item_count"] = max(
            int(documents.get("item_count") or 0),
            1,
        )
        compliance["item_count"] = max(
            int(compliance.get("item_count") or 0),
            1,
        )
        documents["cargo_items_preview"] = [label]
        compliance["cargo_items_preview"] = [label]

        compliance["blockers"] = [
            value
            for value in _as_list(compliance.get("blockers"))
            if "no shipment items were found" not in str(value).lower()
        ]

    payload["special_cargo_controls"] = {
        "applicable": True,
        "status": "blocked",
        "control_types": labels,
        "official_verification_required": True,
    }

    return labels


def _rebuild(payload: dict[str, Any]) -> None:
    # Preserve route/trade sections that were already prepared before the
    # final compliance enrichment. Some generic builders do not know about
    # the V59 route-plan card and would otherwise drop it from ui_sections.
    previous_sections = deepcopy(_as_list(payload.get("ui_sections")))
    previous_route_section = next(
        (
            deepcopy(section)
            for section in previous_sections
            if isinstance(section, dict)
            and section.get("section_id") == "route_plan"
        ),
        None,
    )
    route_plan = deepcopy(_as_dict(payload.get("route_plan")))

    builders = [
        (
            "app.booking_readiness_advisor",
            "build_booking_readiness",
            "booking_readiness",
        ),
        (
            "app.final_answer_builder",
            "build_final_answer",
            "final_answer",
        ),
        (
            "app.action_plan_builder",
            "build_action_plan",
            "action_plan",
        ),
        (
            "app.executive_summary_builder",
            "build_executive_summary",
            "executive_summary",
        ),
        (
            "app.ui_sections_builder",
            "build_ui_sections",
            "ui_sections",
        ),
    ]

    for module_name, function_name, key in builders:
        try:
            module = __import__(
                module_name,
                fromlist=[function_name],
            )
            payload[key] = getattr(
                module,
                function_name,
            )(payload)
        except Exception:
            continue

    sections = payload.get("ui_sections")
    if not isinstance(sections, list):
        sections = []
        payload["ui_sections"] = sections

    if any(
        isinstance(section, dict)
        and section.get("section_id") == "route_plan"
        for section in sections
    ):
        return

    route_section = previous_route_section

    if route_section is None and route_plan:
        origin_gateway = _as_dict(route_plan.get("origin_gateway"))
        destination_gateway = _as_dict(
            route_plan.get("destination_gateway")
        )

        bullets: list[Any] = []
        corridor = route_plan.get("indicative_corridor")
        if corridor:
            bullets.append(f"Indicative corridor: {corridor}")

        for stage in _as_list(route_plan.get("route_stages")):
            if isinstance(stage, dict):
                label = (
                    stage.get("summary")
                    or stage.get("description")
                    or stage.get("label")
                    or stage.get("stage")
                )
                if label:
                    bullets.append(label)
            elif stage:
                bullets.append(stage)

        route_section = {
            "section_id": "route_plan",
            "title": "Indicative Route Plan",
            "status": route_plan.get(
                "status",
                "review_required",
            ),
            "summary": route_plan.get(
                "summary",
                "Indicative route prepared for review.",
            ),
            "metrics": {
                "origin_gateway": origin_gateway.get("name"),
                "destination_gateway": destination_gateway.get(
                    "name"
                ),
                "port_selection_basis": route_plan.get(
                    "port_selection_basis"
                ),
                "live_advisories": route_plan.get(
                    "live_advisory_status",
                    "not_connected",
                ),
                "inland_precarriage": bool(
                    route_plan.get("inland_precarriage")
                ),
            },
            "bullets": _unique(bullets),
            "actions": _unique(
                [
                    *_as_list(route_plan.get("cautions")),
                    *_as_list(route_plan.get("recommendations")),
                ]
            ),
        }

    if route_section is None:
        return

    insert_at = len(sections)
    for index, section in enumerate(sections):
        if (
            isinstance(section, dict)
            and section.get("section_id") == "logistics"
        ):
            insert_at = index + 1
            break

    sections.insert(insert_at, route_section)


def _sync_ui(payload: dict[str, Any]) -> None:
    documents = _as_dict(
        payload.get("document_requirements_advice")
    )
    compliance = _as_dict(
        payload.get("trade_compliance_readiness")
    )
    agreement = _as_dict(
        payload.get("trade_agreement_advice")
    )
    pair_control = _as_dict(
        payload.get("country_pair_control")
    )
    cargo_controls = _as_dict(
        payload.get("special_cargo_controls")
    )

    sections = payload.get("ui_sections")
    if not isinstance(sections, list):
        sections = []
        payload["ui_sections"] = sections

    target = None

    for section in sections:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") in {
            "compliance_documents",
            "documents",
            "compliance",
        }:
            target = section
            break

    if target is None:
        target = {
            "section_id": "compliance_documents",
            "title": "Compliance & Documents",
        }
        sections.append(target)

    target["status"] = compliance.get(
        "status",
        documents.get("status", "review_required"),
    )
    target["summary"] = compliance.get(
        "summary",
        documents.get("summary"),
    )

    metrics = _as_dict(target.get("metrics"))
    metrics.update(
        {
            "ready_for_partner_review": compliance.get(
                "ready_for_partner_review"
            ),
            "origin_country": compliance.get(
                "origin_country"
            ),
            "destination_country": compliance.get(
                "destination_country"
            ),
            "incoterm": compliance.get("incoterm"),
            "item_count": compliance.get(
                "item_count",
                documents.get("item_count"),
            ),
            "required_documents": _unique(
                _as_list(documents.get("required_documents"))
            ),
            "conditional_documents": _unique(
                _as_list(
                    documents.get("conditional_documents")
                )
            ),
            "trade_agreement_status": (
                "found_in_official_static_reference"
                if agreement.get(
                    "agreement_exists_in_local_reference"
                )
                else "not_found_in_local_reference"
            ),
            "agreement_name": agreement.get(
                "agreement_name"
            ),
            "preferential_eligibility": agreement.get(
                "preferential_eligibility_status"
            ),
            "proof_of_origin": _unique(
                _as_list(
                    agreement.get(
                        "proof_of_origin_documents"
                    )
                )
            ),
            "country_pair_control": pair_control.get(
                "control_type"
            ),
            "special_control_types": cargo_controls.get(
                "control_types"
            ),
        }
    )
    target["metrics"] = metrics

    target["bullets"] = _unique(
        [
            *_as_list(compliance.get("blockers")),
            *_as_list(compliance.get("missing_information")),
            *_as_list(compliance.get("warnings")),
            *_as_list(compliance.get("compliance_flags")),
            *_as_list(documents.get("warnings")),
        ]
    )

    target["actions"] = _unique(
        [
            *_as_list(compliance.get("recommendations")),
            *_as_list(documents.get("recommendations")),
        ]
    )


def enrich_dynamic_compliance_payload(
    payload: Any,
    original_text: str | None = None,
) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = _request_text(payload, original_text)
    if not text:
        return payload

    reference = _load_reference()
    signals = _cargo_signals(payload, text)

    _remove_false_positive_cargo_mixups(
        payload,
        signals,
    )

    documents, compliance = _ensure_sections(payload)
    origin, destination = _countries(payload)

    if origin:
        documents["origin_country"] = origin
        compliance["origin_country"] = origin

    if destination:
        documents["destination_country"] = destination
        compliance["destination_country"] = destination

    _apply_agreement(
        payload,
        documents,
        origin,
        destination,
        reference,
    )

    country_control = _apply_country_control(
        payload,
        documents,
        compliance,
        origin,
        destination,
        reference,
    )

    cargo_controls = _apply_cargo_controls(
        payload,
        documents,
        compliance,
        text,
        reference,
    )

    documents["required_documents"] = _unique(
        _as_list(documents.get("required_documents"))
        or [
            "Commercial invoice",
            "Packing list",
            "Bill of lading or airway bill",
        ]
    )
    documents["conditional_documents"] = _unique(
        _as_list(documents.get("conditional_documents"))
    )
    documents["warnings"] = _unique(
        _as_list(documents.get("warnings"))
    )
    documents["recommendations"] = _unique(
        _as_list(documents.get("recommendations"))
    )

    compliance["blockers"] = _unique(
        _as_list(compliance.get("blockers"))
    )
    compliance["compliance_flags"] = _unique(
        _as_list(compliance.get("compliance_flags"))
    )
    compliance["warnings"] = _unique(
        _as_list(compliance.get("warnings"))
    )
    compliance["recommendations"] = _unique(
        _as_list(compliance.get("recommendations"))
    )

    if country_control or cargo_controls:
        payload["decision"] = "review_required"
        payload["status"] = "critical_review_required"

    metadata = payload.setdefault("request_metadata", {})
    if isinstance(metadata, dict):
        metadata["dynamic_compliance_docs_v65"] = {
            "status": "applied",
            "country_pair": _pair_key(origin, destination),
            "country_control_applied": country_control,
            "cargo_controls": cargo_controls,
            "false_positive_cargo_cleanup": {
                "hazardous": signals["hazardous"],
                "fragile": signals["fragile"],
                "non_stackable": signals[
                    "non_stackable"
                ],
            },
        }

    _rebuild(payload)
    _sync_ui(payload)

    return payload
# DYNAMIC_COMPLIANCE_FRONTEND_SYNC_V66
# Synchronize the final human-readable answer and item count after V65 has
# finished enriching the structured compliance/document payload.
_enrich_dynamic_compliance_payload_before_v66 = (
    enrich_dynamic_compliance_payload
)


def _v66_cargo_items(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []

    visualizer = _as_dict(payload.get("logistics_visualizer"))
    for item in _as_list(visualizer.get("cargo_mix")):
        section = _as_dict(item)
        name = (
            section.get("item_name")
            or section.get("name")
            or section.get("product_name")
            or section.get("description")
        )
        if name:
            names.append(str(name).strip())

    if not names:
        for key in (
            "document_requirements_advice",
            "trade_compliance_readiness",
        ):
            section = _as_dict(payload.get(key))
            for name in _as_list(section.get("cargo_items_preview")):
                if name:
                    names.append(str(name).strip())

    return [
        str(value)
        for value in _unique(names)
        if str(value).strip()
    ]


def _v66_sync_item_count(payload: dict[str, Any]) -> None:
    names = _v66_cargo_items(payload)
    if not names:
        return

    count = len(names)

    for key in (
        "document_requirements_advice",
        "trade_compliance_readiness",
    ):
        section = _as_dict(payload.get(key))
        if not section:
            continue

        section["item_count"] = count
        section["cargo_items_preview"] = names[:8]

        if key == "trade_compliance_readiness":
            section["blockers"] = [
                value
                for value in _as_list(section.get("blockers"))
                if "no shipment items were found"
                not in str(value).lower()
            ]


def _v66_sync_final_answer(payload: dict[str, Any]) -> None:
    final_answer = _as_dict(payload.get("final_answer"))
    answer_text = final_answer.get("answer_text")

    if isinstance(answer_text, str) and answer_text.strip():
        payload["display_answer"] = answer_text
        payload["frontend_answer"] = answer_text

    headline = final_answer.get("headline")
    if isinstance(headline, str) and headline.strip():
        payload["display_headline"] = headline


def enrich_dynamic_compliance_payload(
    payload: Any,
    original_text: str | None = None,
) -> Any:
    enriched = _enrich_dynamic_compliance_payload_before_v66(
        payload,
        original_text,
    )

    if not isinstance(enriched, dict):
        return enriched

    _v66_sync_item_count(enriched)
    _sync_ui(enriched)
    _v66_sync_final_answer(enriched)

    metadata = enriched.setdefault("request_metadata", {})
    if isinstance(metadata, dict):
        metadata["dynamic_compliance_frontend_sync_v66"] = {
            "status": "applied",
            "item_count": len(_v66_cargo_items(enriched)),
            "display_answer_synchronised": bool(
                _as_dict(enriched.get("final_answer")).get(
                    "answer_text"
                )
            ),
        }

    return enriched

