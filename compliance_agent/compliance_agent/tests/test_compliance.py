"""Unit and integration tests for ComplianceService and the check_product_compliance tool."""

from ..services.compliance_service import ComplianceService
from ..schemas.compliance import ComplianceCheckRequest

from .. import server


class FakeRestrictedProductsRepository:
    """Fake repository for testing ComplianceService in isolation."""

    def find_match(self, normalized_description: str) -> dict | None:
        if "widget" in normalized_description:
            return {
                "product": "Fake Widget",
                "status": "restricted",
                "hazard_class": "9",
                "un_numbers": ["UN9999"],
                "reason": "fake reason",
                "responsible_department": "Fake Department",
                "required_permits": ["Fake Permit"],
                "required_licenses": [],
                "required_certificates": ["Fake Certificate"],
                "notes": "fake notes",
            }
        return None


class FakeHazardClassRepository:
    """Fake repository for testing ComplianceService in isolation."""

    def get_class_info(self, hazard_class: str) -> dict | None:
        if hazard_class == "9":
            return {"name": "Fake Class Name", "description": "fake", "examples": []}
        return None


class TestComplianceServiceIsolated:
    """Unit tests for ComplianceService using fake repositories."""

    def test_matched_product_returns_full_details(self) -> None:
        service = ComplianceService(
            restricted_products_repository=FakeRestrictedProductsRepository(),
            hazard_class_repository=FakeHazardClassRepository(),
            country_restrictions_repository=FakeCountryRestrictionsRepository(),

        )
        response = service.check(ComplianceCheckRequest(product_description="a fake widget"))
        assert response.matched is True
        assert response.status == "restricted"
        assert response.hazard_class_name == "Fake Class Name"
        assert response.required_permits == ["Fake Permit"]

    def test_unmatched_product_returns_unknown_status(self) -> None:
        service = ComplianceService(
            restricted_products_repository=FakeRestrictedProductsRepository(),
            hazard_class_repository=FakeHazardClassRepository(),
            country_restrictions_repository=FakeCountryRestrictionsRepository(),

        )
        response = service.check(ComplianceCheckRequest(product_description="a mystery item"))
        assert response.matched is False
        assert response.status == "unknown"


class TestCheckProductComplianceToolIntegration:
    """Integration tests for the check_product_compliance tool against the real container."""

    def test_lithium_batteries_are_restricted(self) -> None:
        response = server.check_product_compliance("Lithium Batteries")
        assert response.status == "restricted"
        assert "UN3480" in response.un_numbers
        assert "UN38.3 Test Report" in response.required_certificates

    def test_ammunition_is_prohibited(self) -> None:
        response = server.check_product_compliance("ammunition")
        assert response.status == "prohibited"

    def test_tshirt_is_allowed(self) -> None:
        response = server.check_product_compliance("cotton t-shirt")
        assert response.status == "allowed"

    def test_unrecognized_product_is_unknown(self) -> None:
        response = server.check_product_compliance("an unrecognizable made-up item")
        assert response.status == "unknown"
        assert response.matched is False


class FakeCountryRestrictionsRepository:
    """Fake with no restrictions data, for isolated service tests."""

    def get_restrictions(self, country: str) -> dict | None:
        return None