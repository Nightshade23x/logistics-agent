"""Dependency injection container for the Risk Agent MCP server.

This module is the single place responsible for constructing repository
and service instances. server.py should only ever import from this
module, never directly from repositories/ or services/.
"""

from .repositories.country_risk_repository import CountryRiskRepository
from .services.country_risk_service import CountryRiskService
from .repositories.sanctions_repository import SanctionsRepository
from .services.sanctions_service import SanctionsService
from .services.risk_assessment_service import RiskAssessmentService


class Container:
    """Holds singleton instances of all repositories and services."""

    def __init__(self) -> None:
        """Build repositories first, then inject them into services."""
        country_risk_repository = CountryRiskRepository()

        self.country_risk_service: CountryRiskService = CountryRiskService(
            country_risk_repository=country_risk_repository,
        )

        sanctions_repository = SanctionsRepository()

        self.sanctions_service: SanctionsService = SanctionsService(
            sanctions_repository=sanctions_repository,
        )

        self.risk_assessment_service: RiskAssessmentService = RiskAssessmentService(
            country_risk_service=self.country_risk_service,
            sanctions_service=self.sanctions_service,
        )


def build_container() -> Container:
    """Factory function that builds and returns a fully wired Container.

    Returns:
        A Container instance with all repositories and services instantiated.
    """
    return Container()