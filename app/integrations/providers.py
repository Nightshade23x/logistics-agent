from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import httpx

from app.integrations.contracts import get_path, normalized_quote, set_path, utc_now_iso


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    display_name: str
    provider_type: str
    enabled: bool = True
    environment: str = "sandbox"
    base_url: str | None = None
    quote_path: str | None = None
    health_path: str | None = None
    timeout_seconds: float = 15.0
    auth: dict[str, Any] = field(default_factory=dict)
    request_map: dict[str, str] = field(default_factory=dict)
    response_map: dict[str, str] = field(default_factory=dict)
    capabilities: tuple[str, ...] = ("quotes",)

    def credential_env_names(self) -> list[str]:
        names = []
        for key in ("api_key_env", "token_env", "username_env", "password_env"):
            value = str(self.auth.get(key) or "").strip()
            if value:
                names.append(value)
        return names

    def credentials_configured(self) -> bool:
        auth_type = str(self.auth.get("type") or "none").lower()
        if auth_type == "none":
            return True
        names = self.credential_env_names()
        return bool(names) and all(bool(os.getenv(name)) for name in names)

    def describe(self) -> dict[str, Any]:
        configured = self.provider_type == "mock" or bool(
            self.base_url and self.quote_path and self.credentials_configured()
        )
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_type": self.provider_type,
            "enabled": self.enabled,
            "environment": self.environment,
            "configured": configured,
            "live": self.provider_type != "mock" and self.environment == "production",
            "capabilities": list(self.capabilities),
            "credential_env_names": self.credential_env_names(),
            "credentials_configured": self.credentials_configured(),
            "base_url_configured": bool(self.base_url),
            "quote_endpoint_configured": bool(self.quote_path),
        }


class CarrierProvider(ABC):
    def __init__(self, spec: ProviderSpec):
        self.spec = spec

    def describe(self) -> dict[str, Any]:
        return self.spec.describe()

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def quote(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MockCarrierProvider(CarrierProvider):
    """Deterministic demo provider. It never presents its result as a live rate."""

    def health(self) -> dict[str, Any]:
        return {
            "provider_id": self.spec.provider_id,
            "status": "available",
            "live": False,
            "summary": "Demo quote provider is available. Results are illustrative, not carrier prices.",
            "checked_at": utc_now_iso(),
        }

    def quote(self, request: dict[str, Any]) -> dict[str, Any]:
        weight = float(request.get("total_weight_kg") or 0)
        cbm = float(request.get("total_cbm") or 0)
        chargeable_kg = max(weight, cbm * 167.0, 1.0)
        hazardous_factor = 1.28 if request.get("hazardous") else 1.0
        route_factor = 1.12 if request["origin_country"].lower() != request["destination_country"].lower() else 1.0
        economy = (55.0 + chargeable_kg * 1.22) * hazardous_factor * route_factor
        priority = economy * 1.42
        warning = "Demo estimate only. Connect an approved carrier API for an account-based live quote."

        quotes = [
            normalized_quote(
                provider_id=self.spec.provider_id,
                provider_name=self.spec.display_name,
                service_code="DEMO_ECONOMY",
                service_name="Demo Economy Freight",
                amount=economy,
                currency=request["currency"],
                source="mock_estimate",
                live=False,
                transit_days_min=7,
                transit_days_max=12,
                warnings=[warning],
            ),
            normalized_quote(
                provider_id=self.spec.provider_id,
                provider_name=self.spec.display_name,
                service_code="DEMO_PRIORITY",
                service_name="Demo Priority Freight",
                amount=priority,
                currency=request["currency"],
                source="mock_estimate",
                live=False,
                transit_days_min=3,
                transit_days_max=6,
                warnings=[warning],
            ),
        ]
        return {"status": "ok", "quotes": quotes, "error": None}


class GenericRestProvider(CarrierProvider):
    """Configurable REST adapter for company or carrier APIs.

    Secrets are referenced by environment-variable name in configuration and are
    read only when a request is sent. They are never returned in status payloads.
    """

    def _url(self, path: str | None) -> str:
        if not self.spec.base_url or not path:
            raise ValueError("Provider base_url and endpoint path must be configured.")
        return urljoin(self.spec.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth = self.spec.auth
        auth_type = str(auth.get("type") or "none").lower()

        if auth_type == "api_key":
            env_name = str(auth.get("api_key_env") or "")
            value = os.getenv(env_name)
            if not value:
                raise ValueError(f"Required credential environment variable is missing: {env_name}")
            headers[str(auth.get("header") or "X-API-Key")] = value
        elif auth_type == "bearer":
            env_name = str(auth.get("token_env") or "")
            value = os.getenv(env_name)
            if not value:
                raise ValueError(f"Required credential environment variable is missing: {env_name}")
            headers["Authorization"] = f"Bearer {value}"
        elif auth_type == "basic":
            username_env = str(auth.get("username_env") or "")
            password_env = str(auth.get("password_env") or "")
            username = os.getenv(username_env)
            password = os.getenv(password_env)
            if username is None or password is None:
                raise ValueError("Required basic-auth credential environment variables are missing.")
            token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        elif auth_type != "none":
            raise ValueError(f"Unsupported auth type: {auth_type}")

        for key, value in dict(auth.get("static_headers") or {}).items():
            headers[str(key)] = str(value)
        return headers

    def _request_body(self, request: dict[str, Any]) -> dict[str, Any]:
        if not self.spec.request_map:
            return {key: value for key, value in request.items() if key != "metadata"}

        body: dict[str, Any] = {}
        for internal_field, provider_path in self.spec.request_map.items():
            if internal_field in request:
                set_path(body, provider_path, request.get(internal_field))
        return body

    def health(self) -> dict[str, Any]:
        description = self.describe()
        if not description["configured"]:
            return {
                "provider_id": self.spec.provider_id,
                "status": "not_configured",
                "live": description["live"],
                "summary": "Provider exists but its endpoint or credentials are incomplete.",
                "checked_at": utc_now_iso(),
            }

        if not self.spec.health_path:
            return {
                "provider_id": self.spec.provider_id,
                "status": "configured",
                "live": description["live"],
                "summary": "Provider is configured; no health endpoint was supplied.",
                "checked_at": utc_now_iso(),
            }

        try:
            response = httpx.get(
                self._url(self.spec.health_path),
                headers=self._headers(),
                timeout=self.spec.timeout_seconds,
            )
            response.raise_for_status()
            return {
                "provider_id": self.spec.provider_id,
                "status": "available",
                "live": description["live"],
                "summary": f"Health endpoint returned HTTP {response.status_code}.",
                "checked_at": utc_now_iso(),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "provider_id": self.spec.provider_id,
                "status": "unavailable",
                "live": description["live"],
                "summary": str(exc),
                "checked_at": utc_now_iso(),
            }

    def quote(self, request: dict[str, Any]) -> dict[str, Any]:
        description = self.describe()
        if not description["configured"]:
            return {
                "status": "not_configured",
                "quotes": [],
                "error": "Provider endpoint or credentials are incomplete.",
            }

        try:
            response = httpx.post(
                self._url(self.spec.quote_path),
                headers=self._headers(),
                json=self._request_body(request),
                timeout=self.spec.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            response_map = self.spec.response_map
            quote_list_path = response_map.get("quotes")
            quote_rows = (
                get_path(payload, quote_list_path, [])
                if quote_list_path
                else payload.get("quotes", []) if isinstance(payload, dict) else []
            )
            if isinstance(quote_rows, dict):
                quote_rows = [quote_rows]
            if not isinstance(quote_rows, list):
                raise ValueError("Configured quote-list path did not resolve to an array.")

            quotes = []
            for index, row in enumerate(quote_rows):
                if not isinstance(row, dict):
                    continue
                amount = get_path(row, response_map.get("amount", "amount"))
                if amount is None:
                    continue
                quotes.append(
                    normalized_quote(
                        provider_id=self.spec.provider_id,
                        provider_name=self.spec.display_name,
                        service_code=str(get_path(row, response_map.get("service_code", "service_code"), f"SERVICE_{index + 1}")),
                        service_name=str(get_path(row, response_map.get("service_name", "service_name"), "Carrier service")),
                        amount=float(amount),
                        currency=str(get_path(row, response_map.get("currency", "currency"), request["currency"])),
                        source="carrier_api",
                        live=description["live"],
                        transit_days_min=get_path(row, response_map.get("transit_days_min", "transit_days_min")),
                        transit_days_max=get_path(row, response_map.get("transit_days_max", "transit_days_max")),
                        warnings=list(get_path(row, response_map.get("warnings", "warnings"), []) or []),
                        raw_reference=str(get_path(row, response_map.get("reference", "reference"), "") or "") or None,
                    )
                )

            return {"status": "ok" if quotes else "no_quotes", "quotes": quotes, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "quotes": [], "error": str(exc)}
