from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.integrations.contracts import CONTRACT_VERSION, QUOTE_REQUEST_FIELDS, normalize_quote_request, utc_now_iso
from app.integrations.providers import GenericRestProvider, MockCarrierProvider, ProviderSpec


ROOT = Path(__file__).resolve().parents[2]


def _truthy(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_external_specs() -> list[ProviderSpec]:
    configured_path = str(os.getenv("CARRIER_INTEGRATIONS_CONFIG") or "").strip()
    path = Path(configured_path) if configured_path else ROOT / "config" / "carrier_integrations.json"
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        return []

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("providers", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Carrier integration config must contain a providers array.")

    specs: list[ProviderSpec] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        provider_id = str(row.get("id") or row.get("provider_id") or "").strip()
        if not provider_id:
            continue
        specs.append(
            ProviderSpec(
                provider_id=provider_id,
                display_name=str(row.get("display_name") or provider_id),
                provider_type=str(row.get("type") or "generic_rest"),
                enabled=_truthy(row.get("enabled"), True),
                environment=str(row.get("environment") or "sandbox"),
                base_url=str(row.get("base_url") or "").strip() or None,
                quote_path=str(row.get("quote_path") or "").strip() or None,
                health_path=str(row.get("health_path") or "").strip() or None,
                timeout_seconds=float(row.get("timeout_seconds") or 15.0),
                auth=dict(row.get("auth") or {}),
                request_map=dict(row.get("request_map") or {}),
                response_map=dict(row.get("response_map") or {}),
                capabilities=tuple(row.get("capabilities") or ["quotes"]),
            )
        )
    return specs


def _providers():
    providers = []
    if _truthy(os.getenv("ENABLE_MOCK_CARRIER"), True):
        providers.append(
            MockCarrierProvider(
                ProviderSpec(
                    provider_id="demo_carrier",
                    display_name="Demo Carrier",
                    provider_type="mock",
                    environment="demo",
                    capabilities=("quotes",),
                )
            )
        )

    for spec in _load_external_specs():
        if spec.provider_type != "generic_rest":
            continue
        providers.append(GenericRestProvider(spec))
    return providers


def get_integration_contract() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "quote_request_fields": list(QUOTE_REQUEST_FIELDS),
        "quote_response_fields": [
            "provider_id",
            "provider_name",
            "service_code",
            "service_name",
            "amount",
            "currency",
            "transit_days_min",
            "transit_days_max",
            "source",
            "live",
            "estimated",
            "retrieved_at",
            "warnings",
            "raw_reference",
        ],
        "supported_auth_types": ["none", "api_key", "bearer", "basic"],
        "supported_provider_types": ["mock", "generic_rest"],
        "future_extension_points": [
            "carrier-specific adapters",
            "tracking",
            "shipment creation",
            "pickup booking",
            "provider-approved browser connector",
        ],
        "security": {
            "outbound_credentials": "Environment variables only; secret values are never returned by status endpoints.",
            "optional_inbound_key": "Set LOGISTICS_INTEGRATION_API_KEY and send X-API-Key.",
        },
    }


def list_integrations() -> dict[str, Any]:
    providers = _providers()
    return {
        "status": "ok",
        "contract_version": CONTRACT_VERSION,
        "providers": [provider.describe() for provider in providers],
        "provider_count": len(providers),
        "live_provider_count": sum(1 for provider in providers if provider.describe()["live"]),
        "message": "Configured providers are listed without exposing credential values.",
    }


def check_integrations() -> dict[str, Any]:
    checks = [provider.health() for provider in _providers() if provider.spec.enabled]
    return {
        "status": "ok" if checks and all(item["status"] in {"available", "configured"} for item in checks) else "review_required",
        "checked_at": utc_now_iso(),
        "providers": checks,
    }


def get_carrier_quotes(payload: dict[str, Any]) -> dict[str, Any]:
    provider_ids = payload.get("provider_ids")
    selected = {str(value) for value in provider_ids or []}
    request = normalize_quote_request(payload)

    quotes = []
    provider_results = []
    for provider in _providers():
        if not provider.spec.enabled:
            continue
        if selected and provider.spec.provider_id not in selected:
            continue
        result = provider.quote(request)
        provider_results.append(
            {
                "provider_id": provider.spec.provider_id,
                "status": result.get("status"),
                "error": result.get("error"),
                "quote_count": len(result.get("quotes") or []),
            }
        )
        quotes.extend(result.get("quotes") or [])

    quotes.sort(key=lambda item: (str(item.get("currency")), float(item.get("amount") or 0)))
    has_error = any(item["status"] == "error" for item in provider_results)
    status = "ok" if quotes and not has_error else "partial" if quotes else "not_configured"

    return {
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "request": request,
        "quotes": quotes,
        "provider_results": provider_results,
        "quote_count": len(quotes),
        "retrieved_at": utc_now_iso(),
        "disclaimer": "Demo estimates and API quotes are planning inputs. Confirm the final carrier charge, service availability, surcharges, customs treatment, and booking terms before execution.",
    }
