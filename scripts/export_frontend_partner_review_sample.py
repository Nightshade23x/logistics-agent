from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


OUTPUT_PATH = Path("docs/frontend_partner_review_sample.json")


class MockFrontendOrchestratorHandler(BaseHTTPRequestHandler):
    received_requests: list[dict[str, Any]] = []

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "agent": "mock_frontend_orchestrator_agent",
                },
            )
            return

        self._send_json(404, {"status": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8", errors="replace")

        try:
            parsed_body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            parsed_body = {"raw_body": raw_body}

        self.received_requests.append(
            {
                "path": self.path,
                "body": parsed_body,
            }
        )

        if self.path != "/orchestrate":
            self._send_json(404, {"status": "not_found"})
            return

        self._send_json(
            200,
            {
                "request_id": "mock-frontend-partner-review",
                "status": "review_required",
                "verdict": "review_required",
                "summary": "Mock partner review completed. Shipment is review-required because this is a demo response.",
                "blockers": [],
                "warnings": [
                    "Mock warning: confirm HS code before final customs filing.",
                    "Mock warning: confirm insurance premium before booking.",
                ],
                "recommendations": [
                    "Display this under Partner Review, not under Agents Called.",
                    "Use review_services_called to show external review services.",
                ],
                "agent_responses": {
                    "risk_agent": {
                        "status": "review_required",
                        "summary": "Mock risk review: moderate cargo handling risk.",
                    },
                    "compliance_agent": {
                        "status": "review_required",
                        "summary": "Mock compliance review: HS code confirmation required.",
                    },
                    "trader_agent": {
                        "status": "review_required",
                        "summary": "Mock trader review: verify duty and FTA assumptions.",
                    },
                    "finance_agent": {
                        "status": "review_required",
                        "summary": "Mock finance review: confirm final landed-cost inputs.",
                    },
                },
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), MockFrontendOrchestratorHandler)
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        os.environ["USE_TRAINED_ROUTER"] = "1"
        os.environ.pop("ENABLE_TRADER_AGENT", None)
        os.environ["TRADE_ORCHESTRATOR_BASE_URL"] = base_url

        from app.user_agent import run_user_agent_from_text

        prompt = (
            "estimate freight and find supplier for 100 ceramic tiles from India to USA. "
            "Use CIF incoterm. Freight quote is 1200 USD. Insurance premium is 250 USD. "
            "Duty rate is 5 percent. Import tax rate is 8 percent."
        )

        response = run_user_agent_from_text(prompt)

        partner_review = response.get("partner_review") or {}
        partner_payload = response.get("partner_review_payload") or {}

        sample = {
            "purpose": "Frontend display sample for partner review / live orchestrator mode.",
            "prompt_used": prompt,
            "important_frontend_note": (
                "agents_called shows internal backend agents. "
                "review_services_called shows external partner review services."
            ),
            "ui_fields_to_display": {
                "status": response.get("status"),
                "agents_called": response.get("agents_called"),
                "review_services_called": response.get("review_services_called"),
                "partner_review_status": response.get("partner_review_status"),
                "partner_review_attempted": response.get("partner_review_attempted"),
                "partner_review_mode": response.get("partner_review_mode"),
                "partner_review_service_called": response.get("partner_review_service_called"),
                "live_orchestrator_configured": response.get("live_orchestrator_configured"),
            },
            "partner_review": partner_review,
            "partner_review_payload": {
                "request_id": partner_payload.get("request_id"),
                "origin": partner_payload.get("origin"),
                "origin_country": partner_payload.get("origin_country"),
                "destination": partner_payload.get("destination"),
                "destination_country": partner_payload.get("destination_country"),
                "incoterm": partner_payload.get("incoterm"),
                "freight_quote_usd": partner_payload.get("freight_quote_usd"),
                "insurance_premium_usd": partner_payload.get("insurance_premium_usd"),
                "duty_rate_percent": partner_payload.get("duty_rate_percent"),
                "import_tax_rate_percent": partner_payload.get("import_tax_rate_percent"),
                "total_cbm": partner_payload.get("total_cbm"),
                "total_weight_kg": partner_payload.get("total_weight_kg"),
                "selected_items": partner_payload.get("selected_items"),
                "items": partner_payload.get("items"),
            },
            "specialist_response_keys": sorted((response.get("specialist_responses") or {}).keys()),
            "mock_orchestrator_requests_received": MockFrontendOrchestratorHandler.received_requests,
        }

        assert "shopping_agent" in (response.get("agents_called") or [])
        assert "logistics_agent" in (response.get("agents_called") or [])
        assert "partner_review_service" in (response.get("review_services_called") or [])

        assert response.get("partner_review_attempted") is True
        assert response.get("partner_review_service_called") is True
        assert response.get("partner_review_mode") == "live_orchestrator"
        assert response.get("live_orchestrator_configured") is True

        assert partner_review, "partner_review missing"
        assert partner_payload.get("origin") == "India"
        assert partner_payload.get("destination") == "USA"
        assert partner_payload.get("incoterm") == "CIF"
        assert partner_payload.get("freight_quote_usd") == 1200.0
        assert partner_payload.get("insurance_premium_usd") == 250.0
        assert partner_payload.get("duty_rate_percent") == 5.0
        assert partner_payload.get("import_tax_rate_percent") == 8.0

        OUTPUT_PATH.write_text(json.dumps(sample, indent=2, default=str), encoding="utf-8")

        print(json.dumps(sample["ui_fields_to_display"], indent=2, default=str))
        print(f"\nWrote {OUTPUT_PATH}")
        print("FRONTEND PARTNER REVIEW SAMPLE EXPORT PASSED")

    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
