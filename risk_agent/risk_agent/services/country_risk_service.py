"""Service responsible for assessing country-level corruption risk."""

from ..repositories.country_risk_repository import CountryRiskRepository
from ..schemas.country_risk import CountryRiskRequest, CountryRiskResponse


class CountryRiskService:
    """Looks up a country's CPI score and derives a simplified risk tier."""

    def __init__(self, country_risk_repository: CountryRiskRepository) -> None:
        """Initialize the CountryRiskService with its repository dependency.

        Args:
            country_risk_repository: Provides CPI score reference data.
        """
        self._country_risk_repository = country_risk_repository

    def get_risk(self, request: CountryRiskRequest) -> CountryRiskResponse:
        """Look up a country's CPI score and derive a risk tier.

        Args:
            request: The validated country risk request.

        Returns:
            A CountryRiskResponse with the CPI score and risk tier, or
            found=False if the country isn't in the reference dataset.
        """
        entry = self._country_risk_repository.get_score(request.country)

        if entry is None:
            return CountryRiskResponse(
                country=request.country,
                found=False,
                cpi_score=None,
                risk_tier=None,
            )

        return CountryRiskResponse(
            country=entry["country"],
            found=True,
            cpi_score=entry["cpi_score"],
            risk_tier=self._score_to_tier(entry["cpi_score"]),
        )

    @staticmethod
    def _score_to_tier(cpi_score: int) -> str:
        """Map a CPI score to a simplified risk tier.

        Thresholds are this service's own bucketing for quick reference,
        not an official Transparency International classification.

        Args:
            cpi_score: The CPI score, 0-100.

        Returns:
            One of 'low', 'medium', 'high', 'severe'.
        """
        if cpi_score >= 70:
            return "low"
        if cpi_score >= 50:
            return "medium"
        if cpi_score >= 30:
            return "high"
        return "severe"