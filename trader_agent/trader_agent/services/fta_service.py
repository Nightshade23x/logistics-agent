"""Service responsible for checking Free Trade Agreements (FTAs) between countries."""

from ..repositories.fta_repository import FtaRepository
from ..schemas.fta import FtaRequest, FtaResponse


class FtaService:
    """Provides lookups for known Free Trade Agreements between country pairs."""

    def __init__(self, repository: FtaRepository) -> None:
        """Initialize the FtaService with an injected repository.

        Args:
            repository: Provides access to FTA reference data.
        """
        self._repository = repository

    def check(self, request: FtaRequest) -> FtaResponse:
        """Check whether a known Free Trade Agreement exists between two countries.

        Args:
            request: The validated FTA check request.

        Returns:
            An FtaResponse describing whether an agreement was found.
        """
        country_a = request.country_from.strip().lower()
        country_b = request.country_to.strip().lower()
        agreement_name = self._repository.find_agreement(country_a, country_b)

        if agreement_name:
            return FtaResponse(
                country_from=request.country_from,
                country_to=request.country_to,
                fta_exists=True,
                agreement_name=agreement_name,
                message=(
                    f"A Free Trade Agreement exists between {request.country_from} "
                    f"and {request.country_to}: {agreement_name}. Preferential duty "
                    f"rates may apply; verify specific product eligibility and "
                    f"rules of origin."
                ),
            )

        return FtaResponse(
            country_from=request.country_from,
            country_to=request.country_to,
            fta_exists=False,
            agreement_name=None,
            message=(
                f"No known Free Trade Agreement found between {request.country_from} "
                f"and {request.country_to} in the current reference table. This does "
                f"not conclusively rule out an agreement; the reference table will "
                f"be expanded in a future iteration."
            ),
        )