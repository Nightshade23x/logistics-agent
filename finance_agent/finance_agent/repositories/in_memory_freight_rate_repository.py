from decimal import Decimal

from finance_agent.finance_agent.repositories.freight_rate_repository import FreightRateRepository


class InMemoryFreightRateRepository(FreightRateRepository):

    RATES = {
        ("India", "USA"): Decimal("12.50"),
        ("India", "Germany"): Decimal("10.20"),
        ("China", "USA"): Decimal("9.80"),
    }

    def get_rate(self, origin: str, destination: str) -> Decimal:
        return self.RATES[(origin, destination)]