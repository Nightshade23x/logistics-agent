from decimal import Decimal

from finance_agent.finance_agent.repositories.insurance_rate_repository import InsuranceRateRepository


class InMemoryInsuranceRateRepository(InsuranceRateRepository):

    DEFAULT_RATE = Decimal("0.02")

    def get_rate(self, shipment_id: str) -> Decimal:
        return self.DEFAULT_RATE