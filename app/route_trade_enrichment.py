from __future__ import annotations

from datetime import datetime, timezone
import heapq
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATEWAY_DATA = ROOT / "data" / "route_gateway_reference_v59.json"
FTA_DATA = ROOT / "trader_agent" / "trader_agent" / "data" / "fta_agreements.json"

COUNTRY_ALIASES = {
    "us": "USA",
    "u.s.": "USA",
    "u.s.a.": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "uk": "UK",
    "united kingdom": "UK",
    "uae": "UAE",
    "united arab emirates": "UAE",
    "turkiye": "Turkey",
    "republic of korea": "South Korea",
    "korea": "South Korea",
}

# This graph is a planning abstraction. It deliberately contains no claim that
# a canal, strait, or sea lane is currently open, safe, or uncongested.
CORRIDOR_EDGES = [
    ("east_asia", "pacific", 0.5, "East Asian coastal waters and the Pacific"),
    ("east_asia", "indian_ocean", 1.0, "South China Sea and Strait of Malacca"),
    ("pacific", "north_atlantic", 2.0, "Pacific approaches, Panama Canal, and North Atlantic"),
    ("pacific", "south_atlantic", 2.0, "Pacific approaches, Panama Canal, and South Atlantic"),
    ("pacific", "caribbean", 1.4, "Pacific approaches and Panama Canal"),
    ("caribbean", "north_atlantic", 0.7, "Caribbean and Atlantic approaches"),
    ("indian_ocean", "south_atlantic", 2.0, "Indian Ocean and Cape of Good Hope"),
    ("south_atlantic", "north_atlantic", 1.0, "Atlantic Ocean"),
    ("north_atlantic", "mediterranean", 1.0, "Strait of Gibraltar and Mediterranean"),
    ("mediterranean", "red_sea", 1.0, "Mediterranean and Suez Canal"),
    ("red_sea", "indian_ocean", 1.0, "Red Sea, Bab el-Mandeb, and Gulf of Aden"),
    ("arabian_sea", "red_sea", 0.55, "Arabian Sea, Gulf of Aden, and Bab el-Mandeb"),
    ("indian_ocean", "arabian_sea", 0.5, "Indian Ocean and Arabian Sea"),
    ("arabian_sea", "persian_gulf", 0.5, "Arabian Sea and Strait of Hormuz"),
    ("north_atlantic", "north_sea", 0.7, "English Channel and North Sea"),
    ("north_sea", "baltic", 0.7, "North Sea and Danish Straits"),
]

LIVE_WARNING = (
    "This is an indicative planning route. Verify current carrier schedules, port acceptance, "
    "canal or strait restrictions, congestion, weather, sanctions, security and maritime advisories "
    "before booking."
)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique(values: list[Any]) -> list[Any]:
    output: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if value in (None, "", [], {}):
            continue
        key = json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list)) else str(value)
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _clean_country(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = re.sub(r"\s+", " ", value).strip(" \t\r\n.,;:")
    if not raw or "port of " in raw.lower():
        return None
    key = raw.lower()
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    if len(raw) > 55:
        return None
    return raw if raw.isupper() and len(raw) <= 4 else " ".join(part.capitalize() for part in raw.split())


def _clean_port(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = re.sub(r"\s+", " ", value).strip(" \t\r\n.,;:")
    raw = re.sub(r"^(?:the\s+)?port\s+of\s+", "", raw, flags=re.IGNORECASE)
    if not raw:
        return None

    # NEGATED_PORT_SELECTION_GUARD_V60
    # Do not treat phrases such as "arrival ports have been selected" or
    # "no destination port is specified" as literal port names.
    lowered = raw.lower()
    placeholder_start = re.compile(
        r"^(?:s\s+)?"
        r"(?:(?:has|have|had|is|are|was|were|be|been)\s+)?"
        r"(?:not\s+)?(?:been\s+)?"
        r"(?:selected|chosen|specified|provided|mentioned|confirmed|known|decided|assigned)\b",
        flags=re.IGNORECASE,
    )
    negative_port_statement = re.compile(
        r"\b(?:no|none|without)\b.*\bports?\b"
        r"|\bports?\b.*\b(?:not|never)\b.*"
        r"\b(?:selected|chosen|specified|provided|mentioned|confirmed|known|decided|assigned)\b",
        flags=re.IGNORECASE,
    )
    if placeholder_start.search(raw) or negative_port_statement.search(raw):
        return None

    if lowered in {
        "unknown",
        "not known",
        "not selected",
        "not specified",
        "not provided",
        "to be confirmed",
        "tbc",
        "n/a",
        "na",
        "none",
    }:
        return None
    return raw


def _source_sections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    executive = _dict(payload.get("executive_summary"))
    return [
        payload,
        _dict(payload.get("handoff_payload")),
        _dict(payload.get("input_resolution")),
        _dict(payload.get("shipment_input")),
        _dict(payload.get("logistics_input")),
        _dict(payload.get("trade_terms_advice")),
        _dict(payload.get("document_requirements_advice")),
        _dict(payload.get("trade_compliance_readiness")),
        _dict(_dict(payload.get("landed_cost_advice")).get("known_inputs")),
        _dict(executive.get("shipment_snapshot")),
    ]


def _trusted_country(payload: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for source in _source_sections(payload):
        for name in names:
            country = _clean_country(source.get(name))
            if country:
                return country
    return None


def _explicit_port_route(text: str) -> dict[str, str | None]:
    raw = str(text or "")
    result: dict[str, str | None] = {
        "origin_port": None,
        "destination_port": None,
        "origin_country": None,
        "destination_country": None,
        "origin_location": None,
        "destination_location": None,
    }

    # SMART_GATEWAY_SELECTION_V64
    # A city-country pair is a location hint, not automatically a port.
    paired_ports = re.search(
        r"\bfrom\s+(?:the\s+)?port\s+of\s+"
        r"(?P<origin_port>[A-Za-z][A-Za-z .'\-/]{1,60}?)\s*,\s*"
        r"(?P<origin_country>[A-Za-z][A-Za-z .'-]{1,50}?)\s+to\s+"
        r"(?:the\s+)?port\s+of\s+"
        r"(?P<destination_port>[A-Za-z][A-Za-z .'\-/]{1,60}?)\s*,\s*"
        r"(?P<destination_country>[A-Za-z][A-Za-z .'-]{1,50}?)"
        r"(?=\s+(?:using|under|with|on)\b|[.;]|$)",
        raw,
        flags=re.IGNORECASE,
    )
    if paired_ports:
        result.update(
            {
                "origin_port": _clean_port(paired_ports.group("origin_port")),
                "destination_port": _clean_port(paired_ports.group("destination_port")),
                "origin_country": _clean_country(paired_ports.group("origin_country")),
                "destination_country": _clean_country(paired_ports.group("destination_country")),
            }
        )
        return result

    paired_locations = re.search(
        r"\bfrom\s+"
        r"(?P<origin_location>[A-Za-z][A-Za-z .'\-/]{1,60}?)\s*,\s*"
        r"(?P<origin_country>[A-Za-z][A-Za-z .'-]{1,50}?)\s+to\s+"
        r"(?P<destination_location>[A-Za-z][A-Za-z .'\-/]{1,60}?)\s*,\s*"
        r"(?P<destination_country>[A-Za-z][A-Za-z .'-]{1,50}?)"
        r"(?=\s+(?:using|under|with|on)\b|[.;]|$)",
        raw,
        flags=re.IGNORECASE,
    )
    if paired_locations:
        result.update(
            {
                "origin_location": _clean_port(paired_locations.group("origin_location")),
                "destination_location": _clean_port(paired_locations.group("destination_location")),
                "origin_country": _clean_country(paired_locations.group("origin_country")),
                "destination_country": _clean_country(paired_locations.group("destination_country")),
            }
        )

    patterns = {
        "origin_port": [
            r"\b(?:departure|origin|loading)\s+ports?\b\s*(?:is|=|:)?\s*(?:port\s+of\s+)?([A-Za-z][A-Za-z .'\-/]{1,60}?)(?=[,.;]|\s+to\b|$)",
            r"\bport\s+of\s+loading\b\s*(?:is|=|:)?\s*(?:port\s+of\s+)?([A-Za-z][A-Za-z .'\-/]{1,60}?)(?=[,.;]|\s+to\b|$)",
        ],
        "destination_port": [
            r"\b(?:arrival|destination|discharge|entry)\s+ports?\b\s*(?:is|=|:)?\s*(?:port\s+of\s+)?([A-Za-z][A-Za-z .'\-/]{1,60}?)(?=[,.;]|$)",
            r"\bport\s+of\s+discharge\b\s*(?:is|=|:)?\s*(?:port\s+of\s+)?([A-Za-z][A-Za-z .'\-/]{1,60}?)(?=[,.;]|$)",
        ],
    }
    for key, options in patterns.items():
        for pattern in options:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match:
                result[key] = _clean_port(match.group(1))
                break

    return result


def _route_countries(payload: dict[str, Any], text: str) -> tuple[str | None, str | None, dict[str, str | None]]:
    explicit = _explicit_port_route(text)
    origin = explicit.get("origin_country")
    destination = explicit.get("destination_country")

    if not origin:
        origin = _trusted_country(payload, ("origin_country", "origin", "country_from", "supplier_country"))
    if not destination:
        destination = _trusted_country(payload, ("destination_country", "destination", "country_to", "target_market"))

    try:
        from app.text_shipment_parser import _extract_route_pair_from_text

        parsed = _extract_route_pair_from_text(text)
    except Exception:
        parsed = {}

    if not origin:
        origin = _clean_country(parsed.get("country_from"))
    if not destination:
        destination = _clean_country(parsed.get("country_to"))

    return origin, destination, explicit


def _gateway_reference() -> dict[str, Any]:
    try:
        data = json.loads(GATEWAY_DATA.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _gateway_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    countries = _dict(data.get("countries"))
    for country, detail in countries.items():
        for gateway in _list(_dict(detail).get("gateways")):
            if not isinstance(gateway, dict):
                continue
            for value in [gateway.get("name"), *_list(gateway.get("aliases"))]:
                if isinstance(value, str) and value.strip():
                    key = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
                    index[key] = {**gateway, "reference_country": country}
    return index


def _match_explicit_gateway(port_name: str | None, data: dict[str, Any]) -> dict[str, Any] | None:
    if not port_name:
        return None

    key = re.sub(r"[^a-z0-9]+", " ", port_name.lower()).strip()
    found = _gateway_index(data).get(key)
    if found:
        return dict(found)

    # Preserve the user-supplied terminal name exactly.
    # Never invent a generic "Port of ..." label.
    return {
        "name": port_name,
        "aliases": [port_name],
        "basin": None,
        "reference_country": None,
        "explicit_unmatched": True,
    }


def _country_gateways(country: str, data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    detail = _dict(_dict(data.get("countries")).get(country))
    gateways = [dict(item) for item in _list(detail.get("gateways")) if isinstance(item, dict)]
    return detail, gateways

# SMART_GATEWAY_SELECTION_V64
def _normalise_location(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _gateway_location_penalty(gateway: dict[str, Any], location: str | None) -> int:
    target = _normalise_location(location)
    if not target:
        return 0

    candidates = [
        gateway.get("name"),
        *_list(gateway.get("aliases")),
        *_list(gateway.get("service_areas")),
    ]
    normalised = [
        _normalise_location(value)
        for value in candidates
        if isinstance(value, str)
    ]

    for value in normalised:
        if not value:
            continue
        if target == value or target in value or value in target:
            return 0

    return 5


def _adjacency() -> dict[str, list[tuple[str, float, str]]]:
    graph: dict[str, list[tuple[str, float, str]]] = {}
    for left, right, cost, label in CORRIDOR_EDGES:
        graph.setdefault(left, []).append((right, cost, label))
        graph.setdefault(right, []).append((left, cost, label))
    return graph


def _shortest_corridor(start: str | None, end: str | None) -> tuple[float, list[str], list[str]]:
    if not start or not end:
        return 9999.0, [], []
    if start == end:
        return 0.0, [start], []

    graph = _adjacency()
    queue: list[tuple[float, str, list[str], list[str]]] = [(0.0, start, [start], [])]
    best: dict[str, float] = {}

    while queue:
        cost, node, nodes, labels = heapq.heappop(queue)
        if node in best and best[node] <= cost:
            continue
        best[node] = cost
        if node == end:
            return cost, nodes, labels
        for neighbor, edge_cost, label in graph.get(node, []):
            heapq.heappush(queue, (cost + edge_cost, neighbor, nodes + [neighbor], labels + [label]))
    return 9999.0, [], []


def _choose_gateways(
    origin: str,
    destination: str,
    explicit: dict[str, str | None],
    data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str], str]:
    origin_detail, origin_candidates = _country_gateways(origin, data)
    destination_detail, destination_candidates = _country_gateways(destination, data)

    explicit_origin = _match_explicit_gateway(explicit.get("origin_port"), data)
    explicit_destination = _match_explicit_gateway(explicit.get("destination_port"), data)

    if explicit_origin:
        origin_candidates = [explicit_origin]
    if explicit_destination:
        destination_candidates = [explicit_destination]

    if not origin_candidates:
        origin_candidates = [{
            "name": f"Carrier-selected export gateway in {origin}",
            "basin": None,
            "reference_country": origin,
            "confirmation_required": True,
        }]
    if not destination_candidates:
        destination_candidates = [{
            "name": f"Carrier-selected import gateway in {destination}",
            "basin": None,
            "reference_country": destination,
            "confirmation_required": True,
        }]

    best_pair: tuple[
        int,
        float,
        int,
        int,
        dict[str, Any],
        dict[str, Any],
        list[str],
    ] | None = None

    for oi, origin_gateway in enumerate(origin_candidates):
        for di, destination_gateway in enumerate(destination_candidates):
            cost, _, labels = _shortest_corridor(
                origin_gateway.get("basin"),
                destination_gateway.get("basin"),
            )

            location_penalty = (
                _gateway_location_penalty(
                    origin_gateway,
                    explicit.get("origin_location"),
                )
                + _gateway_location_penalty(
                    destination_gateway,
                    explicit.get("destination_location"),
                )
            )

            priority = (
                int(origin_gateway.get("priority") or oi + 1)
                + int(destination_gateway.get("priority") or di + 1)
            )
            tie_break = oi * 100 + di

            candidate = (
                location_penalty,
                cost,
                priority,
                tie_break,
                origin_gateway,
                destination_gateway,
                labels,
            )

            if best_pair is None or candidate[:4] < best_pair[:4]:
                best_pair = candidate

    assert best_pair is not None
    _, _, _, _, origin_gateway, destination_gateway, labels = best_pair

    if explicit_origin and explicit_destination:
        basis = "user_supplied_ports"
    elif explicit_origin or explicit_destination:
        basis = "mixed_user_and_reference_ports"
    elif explicit.get("origin_location") or explicit.get("destination_location"):
        basis = "location_and_reference_gateway_selection"
    elif origin_detail or destination_detail:
        basis = "reference_gateway_selection"
    else:
        basis = "carrier_gateway_confirmation_required"

    return origin_gateway, destination_gateway, labels, basis


def _gateway_label(gateway: dict[str, Any], shipment_country: str) -> str:
    name = str(gateway.get("name") or "Unconfirmed gateway")
    gateway_country = gateway.get("gateway_country") or gateway.get("reference_country")
    if gateway_country and gateway_country != shipment_country:
        return f"{name}, {gateway_country}"
    return name


def _build_route_plan(
    origin: str,
    destination: str,
    explicit: dict[str, str | None],
) -> dict[str, Any]:
    data = _gateway_reference()
    origin_detail, _ = _country_gateways(origin, data)
    destination_detail, _ = _country_gateways(destination, data)
    origin_gateway, destination_gateway, corridor_labels, selection_basis = _choose_gateways(
        origin,
        destination,
        explicit,
        data,
    )

    origin_label = _gateway_label(origin_gateway, origin)
    destination_label = _gateway_label(destination_gateway, destination)

    steps: list[str] = []
    inland_precarriage = bool(origin_detail.get("landlocked"))
    inland_oncarriage = bool(destination_detail.get("landlocked"))

    if inland_precarriage:
        note = origin_gateway.get("inland_note") or "Confirm inland road/rail and border arrangements."
        steps.append(f"Inland pre-carriage from {origin} to {origin_label}: {note}.")
    steps.append(f"Export handling and vessel loading at {origin_label}.")
    if corridor_labels:
        steps.extend(f"Ocean leg via {label}." for label in corridor_labels)
    else:
        steps.append("Carrier-selected ocean corridor between the confirmed gateways.")
    steps.append(f"Discharge and import handling at {destination_label}.")
    if inland_oncarriage:
        steps.append(f"Inland on-carriage from {destination_label} to the final destination in {destination}.")

    chokepoint_terms = (
        "Panama Canal",
        "Strait of Gibraltar",
        "Suez Canal",
        "Bab el-Mandeb",
        "Strait of Hormuz",
        "Strait of Malacca",
        "Danish Straits",
        "English Channel",
        "Cape of Good Hope",
    )
    chokepoints = [
        term
        for term in chokepoint_terms
        if any(term.lower() in label.lower() for label in corridor_labels)
    ]

    cautions = [LIVE_WARNING]
    if inland_precarriage or inland_oncarriage:
        cautions.append(
            "Confirm through-bill coverage, border transit formalities, inland insurance, axle/road limits, "
            "rail availability and customs-bond arrangements for the inland leg."
        )
    if origin_gateway.get("confirmation_required") or destination_gateway.get("confirmation_required"):
        cautions.append("At least one gateway is not in the local reference table and must be confirmed with a carrier.")
    if chokepoints:
        cautions.append(
            "Verify live operating conditions for the route's chokepoints before booking: "
            + ", ".join(chokepoints)
            + "."
        )

    corridor = " → ".join([origin_label, *corridor_labels, destination_label])
    return {
        "applicable": True,
        "status": "indicative_review_required",
        "summary": f"Indicative route prepared from {origin} to {destination}.",
        "origin_country": origin,
        "destination_country": destination,
        "origin_gateway": {
            "name": origin_gateway.get("name"),
            "gateway_country": origin_gateway.get("gateway_country") or origin_gateway.get("reference_country") or origin,
            "basin": origin_gateway.get("basin"),
            "user_supplied": bool(explicit.get("origin_port")),
        },
        "destination_gateway": {
            "name": destination_gateway.get("name"),
            "gateway_country": destination_gateway.get("gateway_country") or destination_gateway.get("reference_country") or destination,
            "basin": destination_gateway.get("basin"),
            "user_supplied": bool(explicit.get("destination_port")),
        },
        "port_selection_basis": selection_basis,
        "inland_precarriage_required": inland_precarriage,
        "inland_oncarriage_required": inland_oncarriage,
        "indicative_corridor": corridor,
        "route_steps": steps,
        "chokepoints_to_verify": chokepoints,
        "cautions": cautions,
        "live_advisory_status": "not_connected",
        "live_advisory_checked_at": None,
        "data_basis": data.get("basis") or "indicative_static_gateway_reference",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _read_fta_entries() -> list[dict[str, Any]]:
    try:
        value = json.loads(FTA_DATA.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _find_agreement(origin: str, destination: str) -> str | None:
    try:
        from trader_agent.trader_agent.repositories.fta_repository import FtaRepository

        agreement = FtaRepository().find_agreement(origin.lower(), destination.lower())
        if agreement:
            return str(agreement)
    except Exception:
        pass

    pair = {origin.lower(), destination.lower()}
    for entry in _read_fta_entries():
        countries = {str(value).strip().lower() for value in _list(entry.get("countries"))}
        if countries == pair:
            value = entry.get("agreement_name")
            return str(value) if value else None
    return None


def _origin_documents(origin: str, destination: str, agreement_name: str | None) -> list[str]:
    if not agreement_name:
        return ["Standard certificate of origin if requested by customs, the buyer, a bank, or a letter of credit"]

    pair = (origin.lower(), destination.lower())
    if pair == ("usa", "israel"):
        return ["Signed U.S. Origin Invoice Declaration on the commercial invoice or another qualifying commercial document"]
    if pair == ("israel", "usa"):
        return ["Origin evidence or importer affidavit supporting the U.S.-Israel FTA claim, as requested by U.S. Customs"]
    return [f"Preferential certificate or declaration of origin accepted under {agreement_name}"]


def _build_trade_agreement(origin: str, destination: str) -> dict[str, Any]:
    agreement_name = _find_agreement(origin, destination)
    exists = bool(agreement_name)
    documents = _origin_documents(origin, destination, agreement_name)

    if exists:
        summary = f"Local Trader reference data identifies {agreement_name} for {origin}–{destination} trade."
        eligibility = "not_assessed_requires_hs_code_and_product_specific_rules_of_origin"
        preference = "potentially_available_subject_to_eligibility_and_importer_claim"
        warnings = [
            "Agreement existence does not prove this product qualifies for preferential duty.",
            "Confirm the HS classification, product-specific rules of origin, direct-shipment rules and importer claim requirements.",
        ]
    else:
        summary = (
            f"No agreement was found for {origin}–{destination} in the current local Trader reference table. "
            "This is not conclusive."
        )
        eligibility = "not_assessed"
        preference = "not_established_from_local_reference"
        warnings = [
            "Verify the current official agreement and customs position before assuming standard or preferential duty."
        ]

    return {
        "applicable": True,
        "status": "review_required",
        "summary": summary,
        "origin_country": origin,
        "destination_country": destination,
        "agreement_exists_in_local_reference": exists,
        "agreement_name": agreement_name,
        "preferential_eligibility_status": eligibility,
        "preference_claim_status": preference,
        "proof_of_origin_documents": documents,
        "source": "trader_agent_local_fta_reference",
        "source_status": "reference_only_not_live",
        "official_verification_required": True,
        "warnings": warnings,
        "recommendations": [
            "Confirm the HS code before evaluating preferential eligibility.",
            "Check the agreement's product-specific rules of origin and retain supporting production records.",
            "Confirm the exact proof-of-origin wording or form with the importer, customs broker, freight forwarder or customs authority.",
        ],
    }


def _sync_route_fields(payload: dict[str, Any], origin: str, destination: str, route_plan: dict[str, Any]) -> None:
    payload["origin"] = origin
    payload["origin_country"] = origin
    payload["destination"] = destination
    payload["destination_country"] = destination
    payload["origin_port"] = _dict(route_plan.get("origin_gateway")).get("name")
    payload["destination_port"] = _dict(route_plan.get("destination_gateway")).get("name")

    for section in _source_sections(payload):
        for key in ("origin", "origin_country", "country_from"):
            if key in section or section is payload:
                section[key] = origin
        for key in ("destination", "destination_country", "country_to"):
            if key in section or section is payload:
                section[key] = destination

    handoff = payload.setdefault("handoff_payload", {})
    if isinstance(handoff, dict):
        handoff.update(
            {
                "origin": origin,
                "origin_country": origin,
                "destination": destination,
                "destination_country": destination,
                "origin_port": payload["origin_port"],
                "destination_port": payload["destination_port"],
                "indicative_corridor": route_plan.get("indicative_corridor"),
            }
        )


# CARGO_DOCUMENT_CONDITION_SYNC_V61
def _explicit_cargo_conditions(text: str) -> dict[str, bool]:
    lowered = re.sub(r"\s+", " ", str(text or "").lower())

    dangerous_detail = bool(
        re.search(
            r"\b(?:lithium|battery|radioactive|flammable|explosive|dangerous\s+goods|"
            r"un\s*\d{4}|hazmat|toxic|corrosive)\b",
            lowered,
        )
    )
    non_hazardous = bool(
        re.search(
            r"\b(?:non[-\s]?hazardous|not\s+hazardous|without\s+hazardous|"
            r"does\s+not\s+contain\s+hazardous|contains?\s+no\s+hazardous)\b",
            lowered,
        )
    ) and not dangerous_detail

    non_fragile = bool(
        re.search(r"\b(?:not\s+fragile|non[-\s]?fragile|not\s+breakable)\b", lowered)
    )
    stackable = bool(re.search(r"\bstackable\b", lowered)) and not bool(
        re.search(r"\b(?:non[-\s]?stackable|not\s+stackable|do\s+not\s+stack)\b", lowered)
    )

    return {
        "non_hazardous": non_hazardous,
        "non_fragile": non_fragile,
        "stackable": stackable,
        "ordinary_cargo": non_hazardous and non_fragile and stackable,
    }


def _filter_text_entries(values: Any, forbidden: tuple[str, ...]) -> list[Any]:
    output = []
    for value in _list(values):
        lowered = str(value or "").lower()
        if any(term in lowered for term in forbidden):
            continue
        output.append(value)
    return _unique(output)


def _sync_cargo_specific_documents(payload: dict[str, Any], original_text: str) -> None:
    conditions = _explicit_cargo_conditions(original_text)
    if not any(conditions.values()):
        return

    forbidden_docs: list[str] = []
    forbidden_notes: list[str] = []

    if conditions["non_fragile"]:
        forbidden_docs.extend(["fragile handling", "fragile packing"])
        forbidden_notes.extend(["fragile cargo", "fragile handling"])

    if conditions["stackable"]:
        forbidden_docs.extend(["non-stackable", "non stackable"])
        forbidden_notes.extend(["non-stackable", "non stackable", "do not stack"])

    if conditions["non_hazardous"]:
        forbidden_docs.extend(
            ["dangerous goods", "msds", "safety data sheet", "un38.3", "battery declaration"]
        )
        forbidden_notes.extend(
            ["hazardous cargo", "possible hazardous", "dangerous goods", "carrier acceptance"]
        )

    if conditions["ordinary_cargo"]:
        forbidden_notes.extend(["special cargo details", "special cargo"])

    doc_terms = tuple(_unique(forbidden_docs))
    note_terms = tuple(_unique(forbidden_notes))

    docs = _dict(payload.get("document_requirements_advice"))
    if docs:
        docs["conditional_documents"] = _filter_text_entries(
            docs.get("conditional_documents"), doc_terms
        )
        docs["warnings"] = _filter_text_entries(docs.get("warnings"), note_terms)
        docs["recommendations"] = _filter_text_entries(
            docs.get("recommendations"), doc_terms + note_terms
        )
        payload["document_requirements_advice"] = docs

    compliance = _dict(payload.get("trade_compliance_readiness"))
    if compliance:
        for key in ("blockers", "warnings", "compliance_flags", "recommendations"):
            compliance[key] = _filter_text_entries(
                compliance.get(key), note_terms + doc_terms
            )
        payload["trade_compliance_readiness"] = compliance

    sections = payload.get("ui_sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict) or section.get("section_id") != "compliance_documents":
                continue
            metrics = _dict(section.get("metrics"))
            if metrics:
                metrics["conditional_documents"] = _filter_text_entries(
                    metrics.get("conditional_documents"), doc_terms
                )
                section["metrics"] = metrics
            section["bullets"] = _filter_text_entries(
                section.get("bullets"), note_terms + doc_terms
            )
            section["actions"] = _filter_text_entries(
                section.get("actions"), note_terms + doc_terms
            )


def _sync_documents_and_compliance(
    payload: dict[str, Any],
    agreement: dict[str, Any],
) -> None:
    docs = payload.setdefault("document_requirements_advice", {})
    if not isinstance(docs, dict):
        docs = {}
        payload["document_requirements_advice"] = docs

    origin_docs = _list(agreement.get("proof_of_origin_documents"))
    docs["preferential_origin_documents"] = origin_docs
    conditional = _list(docs.get("conditional_documents"))
    if agreement.get("agreement_exists_in_local_reference"):
        conditional.extend(origin_docs)
    else:
        conditional.extend(origin_docs)
    docs["conditional_documents"] = _unique(conditional)
    docs["trade_agreement_name"] = agreement.get("agreement_name")
    docs["trade_agreement_reference_status"] = (
        "known_agreement_in_local_reference"
        if agreement.get("agreement_exists_in_local_reference")
        else "not_found_in_local_reference"
    )
    docs["recommendations"] = _unique(
        _list(docs.get("recommendations")) + _list(agreement.get("recommendations"))
    )

    compliance = payload.setdefault("trade_compliance_readiness", {})
    if not isinstance(compliance, dict):
        compliance = {}
        payload["trade_compliance_readiness"] = compliance
    compliance["trade_agreement"] = agreement
    compliance["trade_agreement_name"] = agreement.get("agreement_name")
    compliance["preferential_eligibility_status"] = agreement.get("preferential_eligibility_status")
    flags = _list(compliance.get("compliance_flags"))
    flags.append(agreement.get("summary"))
    compliance["compliance_flags"] = _unique(flags)
    compliance["recommendations"] = _unique(
        _list(compliance.get("recommendations")) + _list(agreement.get("recommendations"))
    )
    ready = _list(compliance.get("ready_items"))
    ready.append("Origin and destination were checked against the local Trader agreement reference.")
    compliance["ready_items"] = _unique(ready)


def _route_card(route_plan: dict[str, Any]) -> dict[str, Any]:
    origin_gateway = _dict(route_plan.get("origin_gateway"))
    destination_gateway = _dict(route_plan.get("destination_gateway"))
    return {
        "section_id": "route_plan",
        "title": "Indicative Route Plan",
        "status": "review_required",
        "summary": route_plan.get("summary"),
        "metrics": {
            "origin_gateway": origin_gateway.get("name"),
            "destination_gateway": destination_gateway.get("name"),
            "port_selection_basis": route_plan.get("port_selection_basis"),
            "live_advisories": route_plan.get("live_advisory_status"),
            "inland_precarriage": route_plan.get("inland_precarriage_required"),
        },
        "bullets": _unique(
            [f"Indicative corridor: {route_plan.get('indicative_corridor')}"]
            + _list(route_plan.get("route_steps"))
        )[:8],
        "actions": _unique(_list(route_plan.get("cautions")))[:8],
    }


def _sync_ui_sections(
    payload: dict[str, Any],
    route_plan: dict[str, Any],
    agreement: dict[str, Any],
) -> None:
    sections = payload.get("ui_sections")
    if not isinstance(sections, list):
        sections = []
        payload["ui_sections"] = sections

    route_card = _route_card(route_plan)
    existing_route = next(
        (index for index, section in enumerate(sections)
         if isinstance(section, dict) and section.get("section_id") == "route_plan"),
        None,
    )
    if existing_route is None:
        logistics_index = next(
            (index for index, section in enumerate(sections)
             if isinstance(section, dict) and section.get("section_id") == "logistics"),
            len(sections) - 1,
        )
        sections.insert(max(0, logistics_index + 1), route_card)
    else:
        sections[existing_route] = route_card

    compliance = next(
        (section for section in sections
         if isinstance(section, dict) and section.get("section_id") == "compliance_documents"),
        None,
    )
    if compliance is None:
        compliance = {
            "section_id": "compliance_documents",
            "title": "Compliance & Documents",
            "status": "review_required",
            "summary": agreement.get("summary"),
            "metrics": {},
            "bullets": [],
            "actions": [],
        }
        sections.append(compliance)

    metrics = compliance.setdefault("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
        compliance["metrics"] = metrics
    metrics.update(
        {
            "trade_agreement_status": (
                "known_in_local_reference"
                if agreement.get("agreement_exists_in_local_reference")
                else "not_found_in_local_reference"
            ),
            "agreement_name": agreement.get("agreement_name"),
            "preferential_eligibility": agreement.get("preferential_eligibility_status"),
            "proof_of_origin": "; ".join(_list(agreement.get("proof_of_origin_documents"))),
        }
    )
    compliance["bullets"] = _unique(
        _list(compliance.get("bullets"))
        + [agreement.get("summary")]
        + [
            "Preferential eligibility is separate from agreement existence and requires HS classification plus rules-of-origin review."
        ]
    )[:8]
    compliance["actions"] = _unique(
        _list(compliance.get("actions"))
        + _list(agreement.get("recommendations"))
        + _list(agreement.get("proof_of_origin_documents"))
    )[:8]


def enrich_route_trade_payload(payload: Any, original_text: Any = None) -> Any:
    if not isinstance(payload, dict):
        return payload

    text = str(
        original_text
        or _dict(payload.get("request_metadata")).get("original_input_source")
        or _dict(payload.get("request_metadata")).get("input_source")
        or ""
    )
    origin, destination, explicit = _route_countries(payload, text)
    if not origin or not destination:
        metadata = payload.setdefault("request_metadata", {})
        if isinstance(metadata, dict):
            metadata["route_trade_enrichment_v59"] = {
                "status": "not_applied",
                "reason": "origin_or_destination_missing",
            }
        return payload

    route_plan = _build_route_plan(origin, destination, explicit)
    agreement = _build_trade_agreement(origin, destination)

    payload["route_plan"] = route_plan
    payload["trade_agreement_advice"] = agreement
    _sync_route_fields(payload, origin, destination, route_plan)
    _sync_documents_and_compliance(payload, agreement)
    _sync_cargo_specific_documents(payload, text)
    _sync_ui_sections(payload, route_plan, agreement)

    metadata = payload.setdefault("request_metadata", {})
    if isinstance(metadata, dict):
        metadata["route_trade_enrichment_v59"] = {
            "status": "applied",
            "route_basis": route_plan.get("port_selection_basis"),
            "agreement_found": agreement.get("agreement_exists_in_local_reference"),
            "live_advisory_status": route_plan.get("live_advisory_status"),
        }
    return payload
