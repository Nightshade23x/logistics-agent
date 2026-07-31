from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


CONTRACT_VERSION = "carrier-quotes.v1"

QUOTE_REQUEST_FIELDS = (
    "origin_country",
    "destination_country",
    "total_weight_kg",
    "total_cbm",
    "package_count",
    "declared_value_usd",
    "currency",
    "hazardous",
    "pickup_postal_code",
    "delivery_postal_code",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def normalize_quote_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Quote request must be a JSON object.")

    origin = str(payload.get("origin_country") or "").strip()
    destination = str(payload.get("destination_country") or "").strip()
    weight = as_float(payload.get("total_weight_kg"))
    cbm = as_float(payload.get("total_cbm"))

    errors: list[str] = []
    if not origin:
        errors.append("origin_country is required")
    if not destination:
        errors.append("destination_country is required")
    if not ((weight is not None and weight > 0) or (cbm is not None and cbm > 0)):
        errors.append("Provide a positive total_weight_kg or total_cbm")

    if errors:
        raise ValueError("; ".join(errors))

    currency = str(payload.get("currency") or "USD").strip().upper() or "USD"

    return {
        "origin_country": origin,
        "destination_country": destination,
        "total_weight_kg": weight,
        "total_cbm": cbm,
        "package_count": as_int(payload.get("package_count"), 1),
        "declared_value_usd": as_float(payload.get("declared_value_usd")),
        "currency": currency,
        "hazardous": bool(payload.get("hazardous", False)),
        "pickup_postal_code": str(payload.get("pickup_postal_code") or "").strip() or None,
        "delivery_postal_code": str(payload.get("delivery_postal_code") or "").strip() or None,
        "metadata": dict(payload.get("metadata") or {}),
    }


def set_path(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = [part for part in str(dotted_path or "").split(".") if part]
    if not parts:
        return

    current = target
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def get_path(source: Any, dotted_path: str | None, default: Any = None) -> Any:
    if not dotted_path:
        return source

    current = source
    for part in str(dotted_path).split("."):
        if isinstance(current, dict):
            current = current.get(part, default)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return default
            current = current[index]
        else:
            return default
    return current


def normalized_quote(
    *,
    provider_id: str,
    provider_name: str,
    service_code: str,
    service_name: str,
    amount: float,
    currency: str,
    source: str,
    live: bool,
    transit_days_min: int | None = None,
    transit_days_max: int | None = None,
    warnings: list[str] | None = None,
    raw_reference: str | None = None,
) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "provider_name": provider_name,
        "service_code": service_code,
        "service_name": service_name,
        "amount": round(float(amount), 2),
        "currency": str(currency or "USD").upper(),
        "transit_days_min": transit_days_min,
        "transit_days_max": transit_days_max,
        "source": source,
        "live": bool(live),
        "estimated": not bool(live),
        "retrieved_at": utc_now_iso(),
        "warnings": list(warnings or []),
        "raw_reference": raw_reference,
    }
