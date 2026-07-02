"""
Router: single entry point for other agents/systems to reach the Finance Agent.
Dispatches inbound requests to the correct service. No calculation logic here.
"""

from abc import abstractmethod
from typing import Union

from finance_agent.finance_agent.core.interfaces import AgentInterface
from finance_agent.finance_agent.schemas.freight import FreightCostRequest, FreightCostResponse
from finance_agent.finance_agent.schemas.insurance import InsuranceCostRequest, InsuranceCostResponse
from finance_agent.finance_agent.schemas.currency import CurrencyConversionRequest, CurrencyConversionResponse
from finance_agent.finance_agent.schemas.cost_estimation import CostEstimationRequest, CostEstimationResponse
from finance_agent.finance_agent.services.freight_cost_service import FreightCostService
from finance_agent.finance_agent.services.insurance_cost_service import InsuranceCostService
from finance_agent.finance_agent.services.currency_conversion_service import CurrencyConversionService
from finance_agent.finance_agent.services.cost_estimation_service import CostEstimationService

FinanceRequestType = Union[
    FreightCostRequest, InsuranceCostRequest, CurrencyConversionRequest, CostEstimationRequest
]
FinanceResponseType = Union[
    FreightCostResponse, InsuranceCostResponse, CurrencyConversionResponse, CostEstimationResponse
]


class FinanceRouter(AgentInterface):
    """Exposes Finance Agent capabilities to other agents via a single interface."""

    def __init__(
        self,
        freight_cost_service: FreightCostService,
        insurance_cost_service: InsuranceCostService,
        currency_conversion_service: CurrencyConversionService,
        cost_estimation_service: CostEstimationService,
    ) -> None:
        self.freight_cost_service = freight_cost_service
        self.insurance_cost_service = insurance_cost_service
        self.currency_conversion_service = currency_conversion_service
        self.cost_estimation_service = cost_estimation_service

    @abstractmethod
    def handle_request(self, request: FinanceRequestType) -> FinanceResponseType:
        """Dispatch an inbound request to the matching service based on its type."""
        if isinstance(request, FreightCostRequest):
            return self.freight_cost_service.execute(request)
        if isinstance(request, InsuranceCostRequest):
            return self.insurance_cost_service.execute(request)
        if isinstance(request, CurrencyConversionRequest):
            return self.currency_conversion_service.execute(request)
        if isinstance(request, CostEstimationRequest):
            return self.cost_estimation_service.execute(request)
        raise TypeError(f"Unsupported request type: {type(request)}")