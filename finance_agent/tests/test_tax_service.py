from decimal import Decimal

from finance_agent.finance_agent.models.shipment import Shipment
from finance_agent.finance_agent.services.tax_service import TaxService


def test_tax():

    shipment = Shipment(
        shipment_id="SHIP001",
        origin="India",
        destination="USA",
        weight_kg=100,
        volume_m3=10,
        cargo_value=Decimal("100000"),
        currency="USD",
        transport_mode="SEA",
        hs_code="123456",
        insurance_required=True,
    )

    service = TaxService()

    tax = service.execute(shipment)

    assert tax == Decimal("18000.00")