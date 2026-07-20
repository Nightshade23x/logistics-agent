"""Service responsible for looking up country-level sanctions information."""

from ..repositories.sanctions_repository import SanctionsRepository
from ..schemas.sanctions import CountrySanctionsRequest, CountrySanctionsResponse


class SanctionsService:
    """Looks up sanctions status and applicable programs for a country."""

    def __init__(self, sanctions_repository: SanctionsRepository) -> None:
        """Initialize the SanctionsService with its repository dependency.

        Args:
            sanctions_repository: Provides sanctions reference data.
        """
        self._sanctions_repository = sanctions_repository

    def get_country(self, request: CountrySanctionsRequest) -> CountrySanctionsResponse:
        """Look up sanctions information for a country.

        Args:
            request: The validated country sanctions request.

        Returns:
            A CountrySanctionsResponse with sanctions status and programs, or
            found=False if the country isn't in the reference dataset.
        """
        entry = self._sanctions_repository.get_country(request.country)

        if entry is None:
            return CountrySanctionsResponse(
                country=request.country,
                found=False,
                sanctions_status="unknown",
                programs=[],
                notes="No sanctions information available.",
            )

        return CountrySanctionsResponse(
            country=entry["country"],
            found=True,
            sanctions_status=entry["sanctions_status"],
            programs=entry["programs"],
            notes=entry["notes"],
        )
