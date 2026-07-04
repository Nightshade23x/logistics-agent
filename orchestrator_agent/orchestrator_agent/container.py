"""Dependency injection container for the Orchestrator Agent."""

from .shared_llm_client import build_llm_provider
from .clients.mcp_client import build_risk_client, build_compliance_client, build_trader_client
from .clients.finance_client import FinanceClient
from .services.shipment_parser_service import ShipmentParserService
from .services.synthesis_service import SynthesisService
from .services.orchestrator_service import OrchestratorService
from .services.verdict_service import VerdictService



class Container:
    def __init__(self) -> None:
        llm = build_llm_provider()

        self.risk_client = build_risk_client()
        self.compliance_client = build_compliance_client()
        self.trader_client = build_trader_client()
        self.finance_client = FinanceClient(base_url="http://127.0.0.1:8003")

        self.parser_service = ShipmentParserService(llm=llm)
        self.synthesis_service = SynthesisService(llm=llm)
        self.verdict_service = VerdictService()


        self.orchestrator_service = OrchestratorService(
            parser_service=self.parser_service,
            synthesis_service=self.synthesis_service,
            verdict_service=self.verdict_service,
            risk_client=self.risk_client,
            compliance_client=self.compliance_client,
            trader_client=self.trader_client,
            finance_client=self.finance_client,
        )


def build_container() -> Container:
    return Container()