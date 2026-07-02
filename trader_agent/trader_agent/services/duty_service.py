"""Service responsible for estimating import duties between countries."""


class DutyService:
    """Provides estimated duty rates for shipments between two countries.

    This initial implementation uses a small in-memory table of flat
    default duty rates, without regard to trade agreements. FTA-adjusted
    rates are the responsibility of FtaService and can be combined with
    this service's output in a later iteration.
    """

    def __init__(self) -> None:
        """Initialize the DutyService with a static default duty rate table."""
        self._default_rate_percent: float = 5.0
        self._hs_code_rate_overrides: dict[str, float] = {
            "8471.30": 0.0,
            "8517.13": 0.0,
            "6109.10": 16.5,
            "6403.99": 20.0,
            "9401.61": 3.0,
            "0901.21": 0.0,
        }

    def calculate(self, country_from: str, country_to: str, hs_code: str) -> str:
        """Calculate an estimated duty rate for a shipment.

        Args:
            country_from: ISO country name/code of the exporting country.
            country_to: ISO country name/code of the importing country.
            hs_code: The HS code of the product being shipped.

        Returns:
            A description of the estimated duty rate and amount basis.
        """
        normalized_hs_code = hs_code.strip()
        rate_percent = self._hs_code_rate_overrides.get(
            normalized_hs_code, self._default_rate_percent
        )

        return (
            f"Estimated duty for HS code '{hs_code}' shipped from "
            f"{country_from} to {country_to}: {rate_percent}% of declared "
            f"customs value. This is a placeholder flat-rate estimate and "
            f"does not account for applicable Free Trade Agreements; use "
            f"check_fta to determine if a preferential rate may apply."
        )