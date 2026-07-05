"""Coordinates parsing, calling all four agents, and synthesizing the result."""

from ..clients.mcp_client import McpAgentClient
from ..clients.finance_client import FinanceClient
from .shipment_parser_service import ShipmentParserService
from .synthesis_service import SynthesisService
from ..schemas.orchestrated_response import OrchestratedResponse
import time
import uuid
from ..logging_config import get_logger

logger = get_logger(__name__)

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
        request_id = str(uuid.uuid4())
        logger.info(f"[{request_id}] Received query: {query!r}")

        start = time.monotonic()
        shipment = self._parser_service.parse(query)
        logger.info(
            f"[{request_id}] Parsed shipment: {shipment.product_description} "
            f"{shipment.country_from} -> {shipment.country_to} "
            f"({time.monotonic() - start:.2f}s)"
        )

        agent_errors: dict[str, str] = {}

        risk_report: dict = {}
        t0 = time.monotonic()
        try:
            risk_report = self._risk_client.call_tool_sync(
                "assess_trade_risk", {"country": shipment.country_to}
            )
            logger.info(f"[{request_id}] risk_agent OK ({time.monotonic() - t0:.2f}s)")
        except Exception as exc:
            logger.error(f"[{request_id}] risk_agent FAILED ({time.monotonic() - t0:.2f}s): {exc}")
            agent_errors["risk_agent"] = str(exc)

        compliance_report: dict = {}
        t0 = time.monotonic()
        try:
            compliance_report = self._compliance_client.call_tool_sync(
                "assess_compliance",
                {
                    "product_description": shipment.product_description,
                    "destination_country": shipment.country_to,
                },
            )
            logger.info(f"[{request_id}] compliance_agent OK ({time.monotonic() - t0:.2f}s)")
        except Exception as exc:
            logger.error(f"[{request_id}] compliance_agent FAILED ({time.monotonic() - t0:.2f}s): {exc}")
            agent_errors["compliance_agent"] = str(exc)

        trader_report: dict = {}
        t0 = time.monotonic()
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
            logger.info(f"[{request_id}] trader_agent OK ({time.monotonic() - t0:.2f}s)")
        except Exception as exc:
            logger.error(f"[{request_id}] trader_agent FAILED ({time.monotonic() - t0:.2f}s): {exc}")
            agent_errors["trader_agent"] = str(exc)

        finance_report: dict = {}
        t0 = time.monotonic()
        try:
            finance_shipment = {
                "shipment_id": request_id,
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
            logger.info(f"[{request_id}] finance_agent OK ({time.monotonic() - t0:.2f}s)")
        except Exception as exc:
            logger.error(f"[{request_id}] finance_agent FAILED ({time.monotonic() - t0:.2f}s): {exc}")
            agent_errors["finance_agent"] = str(exc)

        verdict = self._verdict_service.derive(
            compliance_report, trader_report, finance_report, risk_report, agent_errors
        )
        logger.info(f"[{request_id}] Verdict: {verdict.status}")

        synthesis = self._synthesis_service.synthesize(
            compliance_report, trader_report, finance_report, risk_report, agent_errors
        )

        total_time = time.monotonic() - start
        logger.info(f"[{request_id}] Completed in {total_time:.2f}s")

        return OrchestratedResponse(
            request_id=request_id,
            parsed_shipment=shipment.model_dump(),
            compliance_report=compliance_report,
            trader_report=trader_report,
            finance_report=finance_report,
            risk_report=risk_report,
            agent_errors=agent_errors,
            verdict=verdict,
            synthesis=synthesis,
        )