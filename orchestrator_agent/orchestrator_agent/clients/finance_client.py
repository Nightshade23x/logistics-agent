"""HTTP client for the Finance Agent's REST API."""

import httpx
import os



class FinanceClient:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or os.environ.get("FINANCE_BASE_URL", "http://127.0.0.1:8003")

    def get_report(self, shipment: dict, selling_price: float | None = None) -> dict:
        params = {"selling_price": selling_price} if selling_price is not None else {}
        response = httpx.post(f"{self._base_url}/finance/report", json=shipment, params=params)
        response.raise_for_status()
        return response.json()

    def get_roi(self, report: dict, selling_price: float) -> dict:
        response = httpx.post(
            f"{self._base_url}/finance/roi",
            json={"report": report, "selling_price": selling_price},
        )
        response.raise_for_status()
        return response.json()