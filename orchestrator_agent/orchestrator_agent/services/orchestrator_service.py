"""Coordinates parsing, calling all four agents, and synthesizing the result."""

from ..clients.mcp_client import McpAgentClient
from ..clients.finance_client import FinanceClient
from .shipment_parser_service import ShipmentParserService
from .synthesis_service import SynthesisService
from ..schemas.orchestrated_response import OrchestratedResponse


class OrchestratorService:
    def __init__(
        self,
        parser_service: ShipmentParserService,
        synthesis_service: SynthesisService,
        verdict_service,
        risk_client: McpAgentClient,
        compliance_client: McpAgentClient,
        trader_client: McpAgentClient,
        finance_client: FinanceClient,
    ) -> None:
        self._parser_service = parser_service
        self._synthesis_service = synthesis_service
        self._verdict_service = verdict_service
        self._risk_client = risk_client
        self._compliance_client = compliance_client
        self._trader_client = trader_client
        self._finance_client = finance_client

    def run(self, query: str) -> OrchestratedResponse:
        shipment = self._parser_service.parse(query)
        agent_errors: dict[str, str] = {}

        risk_report: dict = {}
        try:
            risk_report = self._risk_client.call_tool_sync(
                "assess_trade_risk", {"country": shipment.country_to}
            )
        except Exception as exc:
            agent_errors["risk_agent"] = str(exc)

        compliance_report: dict = {}
        try:
            compliance_report = self._compliance_client.call_tool_sync(
                "check_product_compliance",
                {
                    "product_description": shipment.product_description,
                    "destination_country": shipment.country_to,
                },
            )
        except Exception as exc:
            agent_errors["compliance_agent"] = str(exc)

        trader_report: dict = {}
        try:
            trader_report = self._trader_client.call_tool_sync(
                "assess_trade_plan",
                {
                    "product_description": shipment.product_description,
                    "country_from": shipment.country_from,
                    "country_to": shipment.country_to,
                    "target_market": shipment.target_market,
                },
            )
        except Exception as exc:
            agent_errors["trader_agent"] = str(exc)

        finance_report: dict = {}
        try:
            finance_shipment = {
                "shipment_id": "ORCH-001",
                "origin": shipment.country_from,
                "destination": shipment.country_to,
                "weight_kg": shipment.weight_kg,
                "volume_m3": shipment.volume_m3,
                "cargo_value": shipment.cargo_value,
                "currency": shipment.currency,
                "transport_mode": "sea",
                "insurance_required": True,
            }
            finance_report = self._finance_client.get_report(finance_shipment)

            trader_duty_rate = trader_report.get("handoff_payload", {}).get("duty_rate_percent")
            if trader_duty_rate is not None:
                recalculated_duty = round(shipment.cargo_value * (trader_duty_rate / 100), 2)
                duty_difference = recalculated_duty - finance_report["import_duty"]
                finance_report["import_duty"] = recalculated_duty
                finance_report["landed_cost"] = round(
                    finance_report["landed_cost"] + duty_difference, 2
                )
                finance_report["total_cost"] = round(
                    finance_report["total_cost"] + duty_difference, 2
                )
        except Exception as exc:
            agent_errors["finance_agent"] = str(exc)

        verdict = self._verdict_service.derive(
            compliance_report, trader_report, finance_report, risk_report, agent_errors
        )

        synthesis = self._synthesis_service.synthesize(
            compliance_report, trader_report, finance_report, risk_report, agent_errors
        )

        return OrchestratedResponse(
            parsed_shipment=shipment.model_dump(),
            compliance_report=compliance_report,
            trader_report=trader_report,
            finance_report=finance_report,
            risk_report=risk_report,
            agent_errors=agent_errors,
            synthesis=synthesis,
            verdict=verdict,
        ) 