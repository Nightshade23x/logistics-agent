"""Dependency injection container for the Compliance Agent MCP server.

This module is the single place responsible for constructing repository
and service instances. server.py should only ever import from this
module, never directly from repositories/ or services/.
"""

from .repositories.restricted_products_repository import RestrictedProductsRepository
from .repositories.hazard_class_repository import HazardClassRepository
from .services.compliance_service import ComplianceService
from .services.hazard_class_service import HazardClassService
from .repositories.country_restrictions_repository import CountryRestrictionsRepository
from .services.compliance_assessment_service import ComplianceAssessmentService


class Container:
    """Holds singleton instances of all repositories and services."""

    def __init__(self) -> None:
        """Build repositories first, then inject them into services."""
        restricted_products_repository = RestrictedProductsRepository()
        hazard_class_repository = HazardClassRepository()
        country_restrictions_repository = CountryRestrictionsRepository()

        self.compliance_service: ComplianceService = ComplianceService(
            restricted_products_repository=restricted_products_repository,
            hazard_class_repository=hazard_class_repository,
            country_restrictions_repository=country_restrictions_repository,
        )
        self.compliance_assessment_service: ComplianceAssessmentService = ComplianceAssessmentService(
            compliance_service=self.compliance_service,
        )

        
        self.hazard_class_service: HazardClassService = HazardClassService(
            hazard_class_repository=hazard_class_repository,
        )


def build_container() -> Container:
    """Factory function that builds and returns a fully wired Container.

    Returns:
        A Container instance with all repositories and services instantiated.
    """
    return Container()