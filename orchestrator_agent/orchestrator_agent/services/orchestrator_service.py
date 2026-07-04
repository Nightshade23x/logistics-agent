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
        risk_client: McpAgentClient,
        compliance_client: McpAgentClient,
        trader_client: McpAgentClient,
        finance_client: FinanceClient,
    ) -> None:
        self._parser_service = parser_service
        self._synthesis_service = synthesis_service
        self._risk_client = risk_client
        self._compliance_client = compliance_client
        self._trader_client = trader_client
        self._finance_client = finance_client

    def run(self, query: str) -> OrchestratedResponse:
        shipment = self._parser_service.parse(query)

        risk_report = self._risk_client.call_tool_sync(
            "assess_trade_risk", {"country": shipment.country_to}
        )
        compliance_report = self._compliance_client.call_tool_sync(
            "check_product_compliance",
            {
                "product_description": shipment.product_description,
                "destination_country": shipment.country_to,
            },
        )
        trader_report = self._trader_client.call_tool_sync(
            "assess_trade_plan",
            {
                "product_description": shipment.product_description,
                "country_from": shipment.country_from,
                "country_to": shipment.country_to,
                "target_market": shipment.target_market,
            },
        )
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

        synthesis = self._synthesis_service.synthesize(
            compliance_report, trader_report, finance_report, risk_report
        )

        return OrchestratedResponse(
            parsed_shipment=shipment.model_dump(),
            compliance_report=compliance_report,
            trader_report=trader_report,
            finance_report=finance_report,
            risk_report=risk_report,
            synthesis=synthesis,
        )