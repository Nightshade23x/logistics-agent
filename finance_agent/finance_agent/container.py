from finance_agent.finance_agent.repositories.in_memory_exchange_rate_repository import InMemoryExchangeRateRepository
from finance_agent.finance_agent.repositories.in_memory_freight_rate_repository import InMemoryFreightRateRepository
from finance_agent.finance_agent.repositories.in_memory_insurance_rate_repository import InMemoryInsuranceRateRepository

from finance_agent.finance_agent.services.currency_conversion_service import CurrencyConversionService
from finance_agent.finance_agent.services.freight_cost_service import FreightCostService
from finance_agent.finance_agent.services.import_duty_service import ImportDutyService
from finance_agent.finance_agent.services.insurance_cost_service import InsuranceCostService
from finance_agent.finance_agent.services.landed_cost_service import LandedCostService
from finance_agent.finance_agent.services.profit_service import ProfitService
from finance_agent.finance_agent.services.tax_service import TaxService
from finance_agent.finance_agent.services.report_service import ReportService
from finance_agent.finance_agent.services.cost_estimation_service import CostEstimationService
from finance_agent.finance_agent.services.cost_estimation_service import CostEstimationService
from finance_agent.finance_agent.services.roi_service import RoiService


freight_repo = InMemoryFreightRateRepository()
insurance_repo = InMemoryInsuranceRateRepository()
exchange_repo = InMemoryExchangeRateRepository()

freight_service = FreightCostService(freight_repo)
insurance_service = InsuranceCostService(insurance_repo)
currency_service = CurrencyConversionService(exchange_repo)

import_duty_service = ImportDutyService()
tax_service = TaxService()
landed_cost_service = LandedCostService()
profit_service = ProfitService()

cost_estimation_service = CostEstimationService(
    freight_service=freight_service,
    insurance_service=insurance_service,
    import_duty_service=import_duty_service,
    tax_service=tax_service,
    landed_cost_service=landed_cost_service,
)

roi_service = RoiService()

report_service = ReportService(
    cost_estimation_service=cost_estimation_service,
    profit_service=profit_service,
)