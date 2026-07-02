"""Service responsible for estimating import duties between countries."""

from ..repositories.duty_repository import DutyRepository
from ..schemas.duty import DutyRequest, DutyResponse


class DutyService:
    """Provides estimated duty rates for shipments between two countries."""

    def __init__(self, repository: DutyRepository) -> None:
        """Initialize the DutyService with an injected repository.

        Args:
            repository: Provides access to duty rate reference data.
        """
        self._repository = repository

    def calculate(self, request: DutyRequest) -> DutyResponse:
        """Calculate an estimated duty rate for a shipment.

        Args:
            request: The validated duty calculation request.

        Returns:
            A DutyResponse describing the estimated duty rate.
        """
        normalized_hs_code = request.hs_code.strip()
        override_rate = self._repository.get_override_rate(normalized_hs_code)

        if override_rate is not None:
            rate_percent = override_rate
            rate_source = "hs_code_override"
        else:
            rate_percent = self._repository.get_default_rate()
            rate_source = "default_flat_rate"

        return DutyResponse(
            country_from=request.country_from,
            country_to=request.country_to,
            hs_code=request.hs_code,
            duty_rate_percent=rate_percent,
            rate_source=rate_source,
            message=(
                f"Estimated duty for HS code '{request.hs_code}' shipped from "
                f"{request.country_from} to {request.country_to}: {rate_percent}% "
                f"of declared customs value. This is a placeholder estimate and "
                f"does not account for applicable Free Trade Agreements; use "
                f"check_fta to determine if a preferential rate may apply."
            ),
        )