"""
Service responsible for combined cost estimation.
Composes FreightCostService, InsuranceCostService, and
CurrencyConversionService rather than duplicating their logic.
"""

from finance_agent.core.interfaces import FinanceServiceInterface
from finance_agent.schemas.cost_estimation import CostEstimationRequest, CostEstimationResponse
from finance_agent.schemas.freight import FreightCostRequest
from finance_agent.schemas.insurance import InsuranceCostRequest
from finance_agent.schemas.currency import CurrencyConversionRequest
from finance_agent.services.freight_cost_service import FreightCostService
from finance_agent.services.insurance_cost_service import InsuranceCostService
from finance_agent.services.currency_conversion_service import CurrencyConversionService


class CostEstimationService(FinanceServiceInterface):
    """Combines freight and insurance cost into a total, optionally converted currency."""

    def __init__(
        self,
        freight_cost_service: FreightCostService,
        insurance_cost_service: InsuranceCostService,
        currency_conversion_service: CurrencyConversionService,
    ) -> None:
        self.freight_cost_service = freight_cost_service
        self.insurance_cost_service = insurance_cost_service
        self.currency_conversion_service = currency_conversion_service

    def execute(self, request: CostEstimationRequest) -> CostEstimationResponse:
        """Calculate total_cost = freight_cost + insurance_cost, converted if needed."""
        freight_response = self.freight_cost_service.execute(
            FreightCostRequest(
                shipment_id=request.shipment_id,
                weight_kg=request.weight_kg,
                origin=request.origin,
                destination=request.destination,
                currency=request.currency,
            )
        )
        insurance_response = self.insurance_cost_service.execute(
            InsuranceCostRequest(
                shipment_id=request.shipment_id,
                declared_value=request.declared_value,
                currency=request.currency,
            )
        )

        subtotal = freight_response.freight_cost + insurance_response.insurance_cost
        result_currency = request.currency

        if request.target_currency != request.currency:
            conversion = self.currency_conversion_service.execute(
                CurrencyConversionRequest(
                    amount=subtotal,
                    from_currency=request.currency,
                    to_currency=request.target_currency,
                )
            )
            subtotal = conversion.converted_amount
            result_currency = request.target_currency

        return CostEstimationResponse(
            shipment_id=request.shipment_id,
            freight_cost=freight_response.freight_cost,
            insurance_cost=insurance_response.insurance_cost,
            total_cost=subtotal,
            currency=result_currency,
        )