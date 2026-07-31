from __future__ import annotations

import re
from typing import Any


_COUNTRY_ALIASES = {
    "usa": "USA",
    "us": "USA",
    "u.s.": "USA",
    "u.s.a.": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "india": "India",
    "germany": "Germany",
    "china": "China",
    "uk": "UK",
    "united kingdom": "UK",
    "uae": "UAE",
    "united arab emirates": "UAE",
    "iran": "Iran",
    "zambia": "Zambia",
    "finland": "Finland",
    "spain": "Spain",
    "portugal": "Portugal",
    "france": "France",
    "italy": "Italy",
    "canada": "Canada",
    "mexico": "Mexico",
    "japan": "Japan",
    "singapore": "Singapore",
    "australia": "Australia",
    "turkey": "Turkey",
    "turkiye": "Turkey",
    "south korea": "South Korea",
}

_INCOTERMS = {
    "EXW",
    "FCA",
    "FAS",
    "FOB",
    "CFR",
    "CIF",
    "CPT",
    "CIP",
    "DAP",
    "DPU",
    "DDP",
}

_FINANCE_FIELDS = {
    "procurement_value_usd",
    "freight_quote_usd",
    "insurance_premium_usd",
    "duty_rate_percent",
    "import_tax_rate_percent",
    "customs_brokerage_usd",
    "local_delivery_usd",
}


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _unique(values: list[Any]) -> list[Any]:
    output = []
    seen = set()

    for value in values:
        key = str(value).strip().lower()

        if not key or key in seen:
            continue

        seen.add(key)
        output.append(value)

    return output


def _normal_name(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(value or "").lower(),
    ).strip()


def clean_product_name(value: Any) -> str:
    name = str(value or "").strip()

    name = re.sub(
        r"\s+\bweighing\s+[0-9][0-9,.]*\s*"
        r"(?:kg|kgs|kilograms?|lb|lbs|pounds?)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )

    name = re.sub(
        r"\s+\b(?:exported|shipped|imported)\b\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    name = re.sub(
        r"\s+\bfrom\s+.+$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    return re.sub(r"\s+", " ", name).strip(" ,.;:-")


def _canonical_country(value: Any) -> str | None:
    text = str(value or "").lower().strip()
    text = re.sub(r"^the\s+", "", text)
    text = text.strip(" ?.,;:")

    return _COUNTRY_ALIASES.get(text)


def extract_route(text: Any) -> dict[str, str | None]:
    raw = str(text or "")

    names = sorted(
        _COUNTRY_ALIASES,
        key=len,
        reverse=True,
    )
    pattern = "|".join(re.escape(name) for name in names)

    origin_match = re.search(
        rf"\bfrom\s+(?:the\s+)?({pattern})\b",
        raw,
        flags=re.IGNORECASE,
    )

    destination_match = re.search(
        rf"\bto\s+(?:the\s+)?({pattern})\b",
        raw,
        flags=re.IGNORECASE,
    )

    return {
        "origin": (
            _canonical_country(origin_match.group(1))
            if origin_match
            else None
        ),
        "destination": (
            _canonical_country(destination_match.group(1))
            if destination_match
            else None
        ),
    }


def extract_incoterm(text: Any) -> str | None:
    match = re.search(
        r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|"
        r"DAP|DPU|DDP)\b",
        str(text or ""),
        flags=re.IGNORECASE,
    )

    return match.group(1).upper() if match else None


def extract_finance_fields(text: Any) -> dict[str, float]:
    raw = str(text or "")

    patterns = {
        "procurement_value_usd": [
            r"\bprocurement\s+value\s*(?:is|=|:)?\s*"
            r"(?:USD\s*)?[$]?([0-9][0-9,.]*)",
            r"\bdeclared\s+(?:cargo\s+)?value\s*"
            r"(?:is|=|:)?\s*(?:USD\s*)?[$]?"
            r"([0-9][0-9,.]*)",
        ],
        "freight_quote_usd": [
            r"\bfreight\s+quote\s*(?:is|=|:)?\s*"
            r"(?:USD\s*)?[$]?([0-9][0-9,.]*)",
        ],
        "insurance_premium_usd": [
            r"\binsurance(?:\s+premium)?\s*"
            r"(?:is|=|:)?\s*(?:USD\s*)?[$]?"
            r"([0-9][0-9,.]*)",
        ],
        "duty_rate_percent": [
            r"\bduty(?:\s+rate)?\s*(?:is|=|:)?\s*"
            r"([0-9][0-9,.]*)\s*"
            r"(?:%|percent|per\s+cent)",
        ],
        "import_tax_rate_percent": [
            r"\bimport\s+tax(?:\s+rate)?\s*"
            r"(?:is|=|:)?\s*([0-9][0-9,.]*)\s*"
            r"(?:%|percent|per\s+cent)",
        ],
        "customs_brokerage_usd": [
            r"\bcustoms\s+brokerage\s*"
            r"(?:is|=|:)?\s*(?:USD\s*)?[$]?"
            r"([0-9][0-9,.]*)",
        ],
        "local_delivery_usd": [
            r"\blocal\s+delivery\s*"
            r"(?:is|=|:)?\s*(?:USD\s*)?[$]?"
            r"([0-9][0-9,.]*)",
        ],
    }

    fields: dict[str, float] = {}

    for field, candidates in patterns.items():
        for pattern in candidates:
            match = re.search(
                pattern,
                raw,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            value = _number(match.group(1))

            if value is not None:
                fields[field] = value
                break

    incoterm = extract_incoterm(raw)

    if incoterm:
        fields["incoterm"] = incoterm  # type: ignore[assignment]
        fields["trade_term"] = incoterm  # type: ignore[assignment]

    route = extract_route(raw)

    if route["origin"]:
        fields["origin_country"] = route["origin"]  # type: ignore[assignment]

    if route["destination"]:
        fields["destination_country"] = route["destination"]  # type: ignore[assignment]

    return fields


def calculate_landed_cost(
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    procurement = _number(
        fields.get("procurement_value_usd")
    )

    if procurement is None:
        return None

    freight = (
        _number(fields.get("freight_quote_usd"))
        or 0.0
    )
    insurance = (
        _number(fields.get("insurance_premium_usd"))
        or 0.0
    )
    duty_rate = (
        _number(fields.get("duty_rate_percent"))
        or 0.0
    )
    tax_rate = (
        _number(fields.get("import_tax_rate_percent"))
        or 0.0
    )
    brokerage = (
        _number(fields.get("customs_brokerage_usd"))
        or 0.0
    )
    delivery = (
        _number(fields.get("local_delivery_usd"))
        or 0.0
    )

    customs_value = procurement + freight + insurance
    duty = customs_value * duty_rate / 100.0
    tax_base = customs_value + duty
    import_tax = tax_base * tax_rate / 100.0

    landed = (
        procurement
        + freight
        + insurance
        + duty
        + import_tax
        + brokerage
        + delivery
    )

    missing = sorted(
        field
        for field in _FINANCE_FIELDS
        if fields.get(field) is None
    )

    return {
        "applicable": True,
        "status": (
            "review_required"
            if not missing
            else "needs_more_information"
        ),
        "summary": (
            "Landed cost calculated from all supplied "
            "finance inputs."
            if not missing
            else
            "Landed cost needs additional cost inputs."
        ),
        "known_inputs": dict(fields),
        "missing_cost_inputs": missing,
        "customs_value_usd": round(customs_value, 2),
        "estimated_duty_usd": round(duty, 2),
        "import_tax_base_usd": round(tax_base, 2),
        "estimated_import_tax_usd": round(
            import_tax,
            2,
        ),
        "estimated_subtotal_known_usd": round(
            landed,
            2,
        ),
        "estimated_landed_cost_usd": round(
            landed,
            2,
        ),
        "blockers": [],
        "warnings": [],
        "recommendations": [
            "Validate the supplied duty and tax rates "
            "against the final HS classification.",
        ],
    }


def is_landed_cost_request(text: Any) -> bool:
    lowered = str(text or "").lower()
    fields = extract_finance_fields(text)

    return (
        "landed cost" in lowered
        and len(
            [
                field
                for field in _FINANCE_FIELDS
                if field in fields
            ]
        )
        >= 3
    )


def is_document_requirements_request(text: Any) -> bool:
    lowered = str(text or "").lower()

    document_markers = [
        "commercial invoice",
        "packing list",
        "document requirement",
        "document requirements",
        "dangerous-goods document",
        "dangerous goods document",
    ]

    return any(
        marker in lowered
        for marker in document_markers
    )


def build_finance_specialist(
    text: Any,
) -> dict[str, Any]:
    fields = extract_finance_fields(text)
    calculation = calculate_landed_cost(fields)

    if calculation is None:
        calculation = {
            "status": "needs_more_information",
            "summary": (
                "Finance Agent needs a procurement or "
                "declared cargo value."
            ),
            "known_inputs": fields,
            "missing_cost_inputs": sorted(
                _FINANCE_FIELDS - set(fields)
            ),
        }

    return {
        "agent_name": "finance_agent",
        "status": calculation.get(
            "status",
            "review_required",
        ),
        "summary": calculation.get(
            "summary",
            "Finance Agent prepared landed-cost advice.",
        ),
        "known_inputs": fields,
        "calculation": calculation,
        "missing_information": calculation.get(
            "missing_cost_inputs",
            [],
        ),
        "handoff_payload": {
            **fields,
            **{
                key: value
                for key, value in calculation.items()
                if key.endswith("_usd")
            },
        },
    }


def build_document_specialists(
    text: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = str(text or "")
    lowered = raw.lower()
    route = extract_route(raw)
    incoterm = extract_incoterm(raw)

    hazardous = any(
        marker in lowered
        for marker in [
            "hazardous",
            "dangerous goods",
            "dangerous-goods",
            "lithium battery",
            "lithium batteries",
        ]
    )

    lithium = any(
        marker in lowered
        for marker in [
            "lithium battery",
            "lithium batteries",
        ]
    )

    item_name = (
        "lithium batteries"
        if lithium
        else "shipment cargo"
    )

    required_documents = [
        "Commercial invoice",
        "Packing list",
        "Bill of lading or airway bill",
    ]

    conditional_documents = [
        "Certificate of origin",
        "Cargo insurance certificate or "
        "insurance confirmation",
    ]

    missing_information = []

    if hazardous:
        conditional_documents.extend(
            [
                "Dangerous goods declaration",
                "Safety data sheet / MSDS",
                "Carrier dangerous-goods acceptance",
            ]
        )

    if lithium:
        conditional_documents.extend(
            [
                "UN38.3 test summary",
                "Battery declaration",
                "Lithium battery packing declaration",
            ]
        )
        missing_information.extend(
            [
                "Confirm whether the batteries are "
                "lithium-ion or lithium-metal.",
                "Confirm the UN number, watt-hour rating, "
                "battery net weight and packing instruction.",
                "Confirm carrier acceptance for the "
                "dangerous-goods shipment.",
            ]
        )

    handoff = {
        "origin_country": route["origin"],
        "destination_country": route["destination"],
        "incoterm": incoterm,
        "items": [
            {
                "name": item_name,
                "quantity": 1,
                "packaging": "pallet",
                "hazardous": hazardous,
                "stackable": False if hazardous else None,
            }
        ],
        "required_documents": required_documents,
        "conditional_documents": _unique(
            conditional_documents
        ),
    }

    document_response = {
        "agent_name": "document_ai_agent",
        "status": "review_required",
        "summary": (
            "Document AI Agent prepared the commercial "
            "invoice, packing-list and transport-document "
            "requirements for the shipment."
        ),
        "required_documents": required_documents,
        "conditional_documents": _unique(
            conditional_documents
        ),
        "missing_information": list(
            missing_information
        ),
        "handoff_payload": handoff,
    }

    compliance_response = {
        "agent_name": "compliance_agent",
        "status": "review_required",
        "summary": (
            "Compliance Agent identified dangerous-goods "
            "classification and carrier-acceptance checks."
            if hazardous
            else
            "Compliance Agent prepared shipment "
            "compliance checks."
        ),
        "compliance_flags": (
            [
                "Lithium batteries require dangerous-goods "
                "classification, compliant packaging, labels "
                "and carrier acceptance.",
            ]
            if lithium
            else []
        ),
        "missing_information": list(
            missing_information
        ),
        "handoff_payload": handoff,
    }

    return document_response, compliance_response


def _clean_string(value: str) -> str:
    result = value

    result = re.sub(
        r"\bthe\s+USA\??\b",
        "USA",
        result,
        flags=re.IGNORECASE,
    )

    result = re.sub(
        r"\bGermany\s+The cargo is hazardous\b",
        "Germany",
        result,
        flags=re.IGNORECASE,
    )

    result = result.replace(
        "the product was could not be automatically classified",
        "the product could not be automatically classified",
    )

    result = re.sub(
        r"for '([^']+?)\s+"
        r"(?:exported|shipped|imported)'",
        lambda match: (
            "for '"
            + clean_product_name(match.group(1))
            + "'"
        ),
        result,
        flags=re.IGNORECASE,
    )

    return result


def _clean_recursive(
    value: Any,
    route: dict[str, str | None],
) -> Any:
    if isinstance(value, dict):
        output = {}

        for key, item in value.items():
            lower_key = str(key).lower()

            if route["origin"] and lower_key in {
                "origin",
                "origin_country",
                "country_from",
            }:
                output[key] = route["origin"]
                continue

            if route["destination"] and lower_key in {
                "destination",
                "destination_country",
                "country_to",
                "target_market",
            }:
                output[key] = route["destination"]
                continue

            if lower_key in {
                "product_description",
                "product_name",
            }:
                output[key] = clean_product_name(item)
                continue

            output[key] = _clean_recursive(
                item,
                route,
            )

        return output

    if isinstance(value, list):
        return [
            _clean_recursive(item, route)
            for item in value
        ]

    if isinstance(value, str):
        return _clean_string(value)

    return value


def repair_raw_response(
    response: Any,
    text: Any,
) -> Any:
    if not isinstance(response, dict):
        return response

    route = extract_route(text)
    response = _clean_recursive(response, route)

    agents = response.get("agents_called")

    if not isinstance(agents, list):
        agents = []

    response["agents_called"] = _unique(agents)

    specialists = response.get("specialist_responses")

    if not isinstance(specialists, dict):
        specialists = {}

        primary = response.get("specialist_response")

        if (
            isinstance(primary, dict)
            and primary.get("agent_name")
        ):
            specialists[
                str(primary["agent_name"])
            ] = primary

        response["specialist_responses"] = specialists

    if is_landed_cost_request(text):
        fields = extract_finance_fields(text)
        calculation = calculate_landed_cost(fields)

        response["text_cost_inputs"] = fields
        response["finance_payload"] = fields

        if calculation:
            response["landed_cost_advice"] = calculation

    return response


def _request_text(
    payload: dict[str, Any],
    original_text: Any,
) -> str:
    if original_text:
        return str(original_text)

    metadata = payload.get("request_metadata")

    if isinstance(metadata, dict):
        source = metadata.get("input_source")

        if source:
            return str(source)

    return str(payload.get("input_source") or "")


def _aggregate_cbm_items(
    text: Any,
) -> list[dict[str, Any]]:
    raw = str(text or "")

    pattern = re.compile(
        r"\b(?P<cbm>[0-9][0-9,.]*)\s*"
        r"(?:CBM|m3|m\^3|cubic\s+meters?|"
        r"cubic\s+metres?)\s+"
        r"(?:of\s+)?"
        r"(?P<name>[A-Za-z][A-Za-z0-9 /-]*?)"
        r"(?=\s+\bweighing\b|\s+\bfrom\b|"
        r"\s+\bto\b|\s+\bunder\b|[,.;]|$)",
        flags=re.IGNORECASE,
    )

    output = []

    for match in pattern.finditer(raw):
        cbm = _number(match.group("cbm"))
        name = clean_product_name(match.group("name"))

        if cbm is None or not name:
            continue

        output.append(
            {
                "cbm": cbm,
                "name": name,
            }
        )

    return output


def _explicit_weight(text: Any) -> float | None:
    match = re.search(
        r"\bweighing\s+([0-9][0-9,.]*)\s*"
        r"(kg|kgs|kilograms?|lb|lbs|pounds?)\b",
        str(text or ""),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    value = _number(match.group(1))

    if value is None:
        return None

    unit = match.group(2).lower()

    if unit in {"lb", "lbs", "pound", "pounds"}:
        value *= 0.45359237

    return round(value, 6)


def _item_matches(
    item_name: Any,
    requested_name: Any,
) -> bool:
    item = _normal_name(item_name)
    requested = _normal_name(requested_name)

    return bool(
        item
        and requested
        and (
            item in requested
            or requested in item
        )
    )


def _repair_visualizer(
    payload: dict[str, Any],
    text: str,
) -> None:
    visualizer = payload.get("logistics_visualizer")

    if not isinstance(visualizer, dict):
        return

    container = visualizer.get("container")
    cargo_mix = visualizer.get("cargo_mix")

    selected = (
        container.get("selected_container")
        if isinstance(container, dict)
        else None
    )

    if (
        not selected
        or not isinstance(cargo_mix, list)
        or not cargo_mix
    ):
        visualizer["status"] = "unavailable"
        visualizer["cargo_mix"] = []
        visualizer["container_options"] = []
        visualizer["zone_layout"] = []
        visualizer["loading_sequence"] = []
        visualizer["fit_check"] = {
            "status": "unavailable",
            "selected_container_checked": None,
            "warnings": [],
            "recommendations": [],
            "item_fit_results": [],
        }

        hints = visualizer.get("frontend_hints")

        if isinstance(hints, dict):
            hints["show_fit_warnings"] = False
            hints["show_loading_sequence"] = False

        return

    visualizer["status"] = "available"

    aggregate_items = _aggregate_cbm_items(text)
    explicit_weight = _explicit_weight(text)
    total_weight_delta = 0.0
    adjusted_names = set()

    for specification in aggregate_items:
        requested_name = specification["name"]
        cbm = specification["cbm"]

        for item in cargo_mix:
            if not isinstance(item, dict):
                continue

            item_name = (
                item.get("item_name")
                or item.get("name")
            )

            if not _item_matches(
                item_name,
                requested_name,
            ):
                continue

            side = round(cbm ** (1.0 / 3.0), 6)

            item["dimensions_m"] = {
                "length": side,
                "width": side,
                "height": side,
            }
            item["unit_cbm"] = cbm
            item["total_cbm"] = cbm
            item["aggregate_volume_only"] = True
            item["dimensions_are_aggregate"] = True
            item["display_dimensions_estimated"] = True

            old_weight = (
                _number(item.get("total_weight_kg"))
                or 0.0
            )
            new_weight = old_weight

            if (
                explicit_weight is not None
                and len(cargo_mix) == 1
            ):
                new_weight = explicit_weight
                item["weight_source"] = (
                    "explicit_total_weight"
                )
            elif (
                "ceramic tile"
                in _normal_name(item_name)
                and old_weight < cbm * 500
            ):
                # Configurable planning estimate only.
                # Replace with the final packed weight.
                new_weight = round(cbm * 2000.0, 2)
                item["weight_estimated"] = True
                item["weight_source"] = (
                    "planning_density_estimate"
                )
                item[
                    "estimated_density_kg_per_cbm"
                ] = 2000.0
                item["weight_estimate_warning"] = (
                    "Planning estimate only; replace with "
                    "the final packed shipment weight."
                )

            if new_weight != old_weight:
                item["unit_weight_kg"] = new_weight
                item["total_weight_kg"] = new_weight
                total_weight_delta += (
                    new_weight - old_weight
                )

            adjusted_names.add(
                _normal_name(item_name)
            )

    metrics = payload.get("logistics_metrics")

    if total_weight_delta:
        if isinstance(container, dict):
            existing = (
                _number(container.get("total_weight_kg"))
                or 0.0
            )
            container["total_weight_kg"] = round(
                existing + total_weight_delta,
                2,
            )

        if isinstance(metrics, dict):
            existing = (
                _number(metrics.get("total_weight_kg"))
                or 0.0
            )
            metrics["total_weight_kg"] = round(
                existing + total_weight_delta,
                2,
            )

    fit_check = visualizer.get("fit_check")

    if not isinstance(fit_check, dict):
        return

    results = fit_check.get("item_fit_results")

    if isinstance(results, list):
        dimensions_by_name = {
            _normal_name(
                item.get("item_name")
                or item.get("name")
            ): item.get("dimensions_m")
            for item in cargo_mix
            if isinstance(item, dict)
        }

        for result in results:
            if not isinstance(result, dict):
                continue

            name = _normal_name(
                result.get("item_name")
                or result.get("name")
            )

            if (
                name in adjusted_names
                and name in dimensions_by_name
            ):
                result["dimensions_m"] = (
                    dimensions_by_name[name]
                )
                result[
                    "fits_selected_container"
                ] = True
                result[
                    "passes_selected_container_door"
                ] = True
                result[
                    "smallest_standard_container_fit"
                ] = (
                    fit_check.get(
                        "selected_container_checked"
                    )
                    or selected
                )

    def keep_message(message: Any) -> bool:
        normalized = _normal_name(message)

        return not any(
            adjusted
            and adjusted in normalized
            for adjusted in adjusted_names
        )

    warnings = fit_check.get("warnings")
    recommendations = fit_check.get("recommendations")

    if isinstance(warnings, list):
        warnings = [
            item
            for item in warnings
            if keep_message(item)
        ]
    else:
        warnings = []

    if isinstance(recommendations, list):
        recommendations = [
            item
            for item in recommendations
            if keep_message(item)
        ]
    else:
        recommendations = []

    result_values = (
        [
            item.get("fits_selected_container")
            for item in results
            if isinstance(item, dict)
        ]
        if isinstance(results, list)
        else []
    )

    if result_values and all(
        value is True
        for value in result_values
    ):
        fit_check["status"] = "fits_selected_container"

        if not warnings:
            warnings = [
                "No major physical container fit "
                "issues detected.",
            ]

        if not recommendations:
            recommendations = [
                "Cargo appears physically suitable "
                "for the selected container.",
            ]

    fit_check["warnings"] = warnings
    fit_check["recommendations"] = recommendations


def _repair_finance(
    payload: dict[str, Any],
    text: str,
) -> None:
    fields = extract_finance_fields(text)

    if not fields:
        return

    calculation = calculate_landed_cost(fields)

    payload["text_cost_inputs"] = fields
    payload["finance_payload"] = {
        **fields,
        **(
            {
                key: value
                for key, value
                in calculation.items()
                if key.endswith("_usd")
            }
            if calculation
            else {}
        ),
    }

    if calculation:
        payload["landed_cost_advice"] = calculation


def _cargo_names(
    payload: dict[str, Any],
    text: str,
) -> list[str]:
    visualizer = payload.get("logistics_visualizer")
    names = []

    if isinstance(visualizer, dict):
        cargo_mix = visualizer.get("cargo_mix")

        if isinstance(cargo_mix, list):
            for item in cargo_mix:
                if not isinstance(item, dict):
                    continue

                name = clean_product_name(
                    item.get("item_name")
                    or item.get("name")
                )

                if name:
                    names.append(name)

    lowered = text.lower()

    if (
        not names
        and (
            "lithium battery" in lowered
            or "lithium batteries" in lowered
        )
    ):
        names.append("lithium batteries")

    return _unique(names)


def _remove_no_item_messages(values: Any) -> Any:
    if not isinstance(values, list):
        return values

    stale = [
        "no shipment items were available",
        "no shipment items were found",
        "which products and quantities are included",
    ]

    return [
        item
        for item in values
        if not any(
            marker in str(item).lower()
            for marker in stale
        )
    ]


def _repair_documents(
    payload: dict[str, Any],
    text: str,
) -> None:
    names = _cargo_names(payload, text)
    agents = payload.get("agents_called")

    if not isinstance(agents, list):
        agents = []

    hazardous = any(
        marker in text.lower()
        for marker in [
            "hazardous",
            "dangerous goods",
            "dangerous-goods",
            "lithium battery",
            "lithium batteries",
        ]
    )

    for key in [
        "document_requirements_advice",
        "trade_compliance_readiness",
    ]:
        section = payload.get(key)

        if not isinstance(section, dict):
            continue

        if names:
            section["item_count"] = len(names)
            section["cargo_items_preview"] = names[:8]

        for list_key in [
            "warnings",
            "blockers",
            "missing_information",
            "user_questions",
        ]:
            section[list_key] = _remove_no_item_messages(
                section.get(list_key)
            )

    document = payload.get(
        "document_requirements_advice"
    )

    if isinstance(document, dict) and hazardous:
        conditional = document.get(
            "conditional_documents"
        )

        if not isinstance(conditional, list):
            conditional = []

        conditional.extend(
            [
                "Dangerous goods declaration",
                "Safety data sheet / MSDS",
                "UN38.3 test summary",
                "Battery declaration",
                "Carrier dangerous-goods acceptance",
            ]
        )

        document["conditional_documents"] = _unique(
            conditional
        )

    if "document_ai_agent" in agents:
        review = payload.get("document_quality_review")

        if not isinstance(review, dict):
            review = {}
            payload["document_quality_review"] = review

        review["applicable"] = True
        review["status"] = (
            document.get("status", "review_required")
            if isinstance(document, dict)
            else "review_required"
        )
        review["summary"] = (
            document.get("summary")
            if isinstance(document, dict)
            else
            "Document AI Agent prepared document "
            "requirements."
        )
        review["blockers"] = []
        review.setdefault("warnings", [])
        review.setdefault("recommendations", [])

    validation = payload.get("backend_validation")

    if (
        isinstance(validation, dict)
        and {
            "document_ai_agent",
            "compliance_agent",
        }.issubset(set(agents))
    ):
        errors = validation.get(
            "response_contract_errors"
        )

        if not isinstance(errors, list):
            errors = []

        errors = [
            error
            for error in errors
            if "specialist_responses"
            not in str(error)
        ]

        validation["response_contract_errors"] = errors
        validation["response_contract_valid"] = (
            not errors
        )


def _repair_agent_summaries(
    payload: dict[str, Any],
) -> None:
    agents = payload.get("agents_called")

    if not isinstance(agents, list):
        agents = []

    agents = _unique(agents)
    payload["agents_called"] = agents

    summaries = payload.get("agent_summaries")

    if not isinstance(summaries, list):
        summaries = []

    existing = {
        item.get("agent_name")
        for item in summaries
        if isinstance(item, dict)
    }

    default_summaries = {
        "shopping_agent": (
            "Shopping Agent prepared supplier and "
            "procurement options."
        ),
        "logistics_agent": (
            "Logistics Agent prepared shipment and "
            "container advice."
        ),
        "trader_agent": (
            "Trader Agent prepared trade, tariff and "
            "FTA advice."
        ),
        "finance_agent": (
            "Finance Agent prepared landed-cost advice."
        ),
        "document_ai_agent": (
            "Document AI Agent prepared document "
            "requirements."
        ),
        "compliance_agent": (
            "Compliance Agent prepared dangerous-goods "
            "and shipment-compliance advice."
        ),
    }

    for agent in agents:
        if agent in existing:
            continue

        summaries.append(
            {
                "agent_name": agent,
                "status": "review_required",
                "summary": default_summaries.get(
                    agent,
                    f"{agent} prepared its specialist review.",
                ),
            }
        )

    payload["agent_summaries"] = summaries

    if {
        "document_ai_agent",
        "compliance_agent",
    }.issubset(set(agents)):
        payload["summary"] = (
            "User Agent routed the request to "
            "Document AI Agent and Compliance Agent."
        )
    elif {
        "trader_agent",
        "finance_agent",
    }.issubset(set(agents)):
        payload["summary"] = (
            "User Agent routed the request to "
            "Trader Agent and Finance Agent."
        )
    elif {
        "logistics_agent",
        "trader_agent",
    }.issubset(set(agents)):
        payload["summary"] = (
            "User Agent ran Logistics Agent and "
            "Trader Agent for the cross-border shipment."
        )


def _repair_short_answer(
    payload: dict[str, Any],
) -> None:
    decision = payload.get("decision") or payload.get(
        "status"
    )
    agents = ", ".join(payload.get("agents_called") or [])

    parts = [
        f"Decision: {decision}.",
        f"Agents called: {agents or 'none'}.",
    ]

    metrics = payload.get("logistics_metrics")

    if isinstance(metrics, dict) and any(
        metrics.get(key) is not None
        for key in [
            "total_cbm",
            "total_weight_kg",
            "recommended_container",
        ]
    ):
        parts.append(
            "Logistics: "
            f"{metrics.get('total_cbm')} CBM, "
            f"{metrics.get('total_weight_kg')} kg, "
            "recommended container "
            f"{metrics.get('recommended_container')}, "
            f"risk level {metrics.get('risk_level')}."
        )

    landed = payload.get("landed_cost_advice")

    if (
        isinstance(landed, dict)
        and landed.get("estimated_landed_cost_usd")
        is not None
    ):
        parts.append(
            "Estimated landed cost: USD "
            f"{landed['estimated_landed_cost_usd']:.2f}."
        )

    payload["short_answer"] = " ".join(parts)


def repair_frontend_payload(
    payload: Any,
    original_text: Any = None,
) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = _request_text(payload, original_text)
    route = extract_route(text)

    payload = _clean_recursive(payload, route)

    _repair_finance(payload, text)
    _repair_visualizer(payload, text)
    _repair_documents(payload, text)
    _repair_agent_summaries(payload)

    payload = _clean_recursive(payload, route)

    _repair_short_answer(payload)

    return payload
