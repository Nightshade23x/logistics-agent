from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Shipment:
    """
    Core shipment model used by the Finance Agent.

    Represents all financial information required to estimate
    shipment-related costs.
    """

    shipment_id: str

    origin: str
    destination: str

    weight_kg: float
    volume_m3: float

    cargo_value: Decimal
    currency: str

    transport_mode: str

    hs_code: Optional[str] = None

    insurance_required: bool = False