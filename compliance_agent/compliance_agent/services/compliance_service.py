"""Service responsible for checking product trade compliance status."""

from ..repositories.restricted_products_repository import RestrictedProductsRepository
from ..repositories.hazard_class_repository import HazardClassRepository
from ..schemas.compliance import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    BatchComplianceCheckRequest,
    BatchComplianceCheckResponse,
)


class ComplianceService:
    """Checks whether a product is allowed, restricted, or prohibited for trade."""

    def __init__(
        self,
        restricted_products_repository: RestrictedProductsRepository,
        hazard_class_repository: HazardClassRepository,
    ) -> None:
        """Initialize the ComplianceService with its two repository dependencies.

        Args:
            restricted_products_repository: Provides product-level compliance data.
            hazard_class_repository: Provides IMDG hazard class reference data.
        """
        self._restricted_products_repository = restricted_products_repository
        self._hazard_class_repository = hazard_class_repository

    def check(self, request: ComplianceCheckRequest) -> ComplianceCheckResponse:
        """Check the compliance status of a product description.

        Args:
            request: The validated compliance check request.

        Returns:
            A ComplianceCheckResponse describing the product's status,
            hazard classification, and any required permits, licenses,
            or certificates.
        """
        normalized_description = request.product_description.strip().lower()
        entry = self._restricted_products_repository.find_match(normalized_description)

        if entry is None:
            return ComplianceCheckResponse(
                product_description=request.product_description,
                matched=False,
                matched_product=None,
                status="unknown",
                hazard_class=None,
                hazard_class_name=None,
                un_numbers=[],
                reason=(
                    f"No compliance data found for '{request.product_description}'. "
                    f"This does not confirm the product is safe to trade; it simply "
                    f"means it is not yet in the reference dataset. Verify manually "
                    f"with the relevant customs or regulatory authority."
                ),
                responsible_department=None,
                required_permits=[],
                required_licenses=[],
                required_certificates=[],
                notes=None,
            )

        hazard_class = entry.get("hazard_class")
        hazard_class_name = None
        if hazard_class is not None:
            class_info = self._hazard_class_repository.get_class_info(hazard_class)
            if class_info is not None:
                hazard_class_name = class_info["name"]

        return ComplianceCheckResponse(
            product_description=request.product_description,
            matched=True,
            matched_product=entry["product"],
            status=entry["status"],
            hazard_class=hazard_class,
            hazard_class_name=hazard_class_name,
            un_numbers=entry.get("un_numbers", []),
            reason=entry["reason"],
            responsible_department=entry.get("responsible_department"),
            required_permits=entry.get("required_permits", []),
            required_licenses=entry.get("required_licenses", []),
            required_certificates=entry.get("required_certificates", []),
            notes=entry.get("notes"),
        )

    def check_batch(self, request: BatchComplianceCheckRequest) -> BatchComplianceCheckResponse:
        """Check the compliance status of multiple product descriptions at once.

        Reuses check() for each item rather than duplicating lookup logic,
        so the two tools can never disagree on how a single product resolves.

        Args:
            request: The validated batch compliance check request.

        Returns:
            A BatchComplianceCheckResponse with one result per input product,
            plus summary counts of restricted/prohibited/unknown items.
        """
        results = [
            self.check(ComplianceCheckRequest(product_description=description))
            for description in request.product_descriptions
        ]

        return BatchComplianceCheckResponse(
            results=results,
            restricted_count=sum(1 for r in results if r.status == "restricted"),
            prohibited_count=sum(1 for r in results if r.status == "prohibited"),
            unknown_count=sum(1 for r in results if r.status == "unknown"),
        )