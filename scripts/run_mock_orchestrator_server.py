from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


HOST = "127.0.0.1"
PORT = 8010


class MockOrchestratorHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
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
                    "agent": "mock_orchestrator_agent",
                    "note": "Mock server for frontend/backend live partner testing.",
                },
            )
            return

        self._send_json(404, {"status": "not_found", "path": self.path})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8", errors="replace")

        try:
            parsed_body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            parsed_body = {"raw_body": raw_body}

        print()
        print("=" * 80)
        print("MOCK ORCHESTRATOR RECEIVED REQUEST")
        print("=" * 80)
        print("Path:", self.path)
        print(json.dumps(parsed_body, indent=2, default=str))

        if self.path != "/orchestrate":
            self._send_json(404, {"status": "not_found", "path": self.path})
            return

        self._send_json(
            200,
            {
                "request_id": "mock-live-ui-review",
                "status": "review_required",
                "verdict": "review_required",
                "summary": (
                    "Mock live partner review completed successfully. "
                    "This proves the frontend/backend live partner path is wired."
                ),
                "blockers": [],
                "warnings": [
                    "Mock warning: confirm HS code before final customs filing.",
                    "Mock warning: confirm insurance premium before booking.",
                ],
                "recommendations": [
                    "Display this under Partner Review, not Agents Called.",
                    "Use review_services_called for partner/orchestrator services.",
                ],
                "agent_responses": {
                    "risk_agent": {
                        "status": "review_required",
                        "summary": "Mock risk review: moderate handling risk.",
                    },
                    "compliance_agent": {
                        "status": "review_required",
                        "summary": "Mock compliance review: HS code confirmation required.",
                    },
                    "trader_agent": {
                        "status": "review_required",
                        "summary": "Mock trader review: duty and FTA assumptions should be verified.",
                    },
                    "finance_agent": {
                        "status": "review_required",
                        "summary": "Mock finance review: landed-cost inputs need final confirmation.",
                    },
                },
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = HTTPServer((HOST, PORT), MockOrchestratorHandler)
    print(f"Mock orchestrator running on http://{HOST}:{PORT}")
    print("Health:      http://127.0.0.1:8010/health")
    print("Orchestrate: http://127.0.0.1:8010/orchestrate")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopping mock orchestrator.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
