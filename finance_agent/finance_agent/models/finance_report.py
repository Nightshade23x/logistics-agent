from dataclasses import dataclass
from decimal import Decimal


@dataclass
class FinanceReport:
    shipment_id: str

    freight_cost: Decimal

    insurance_cost: Decimal

    import_duty: Decimal

    taxes: Decimal

    landed_cost: Decimal

    currency: str

    total_cost: Decimal

    estimated_profit: Decimal = Decimal("0.00")