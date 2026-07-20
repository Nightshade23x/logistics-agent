"""Tests for destination-country-aware compliance checks."""

from ..services.compliance_service import ComplianceService
from ..schemas.compliance import ComplianceCheckRequest, BatchComplianceCheckRequest
from .. import server


class FakeRestrictedProductsRepository:
    def find_match(self, normalized_description: str):
        if "batter" in normalized_description:
            return {
                "product": "Lithium-ion batteries (standalone)",
                "status": "restricted",
                "hazard_class": "9",
                "un_numbers": ["UN3480"],
                "reason": "Thermal runaway risk.",
                "responsible_department": "IATA",
                "required_permits": [],
                "required_licenses": [],
                "required_certificates": [],
                "notes": None,
            }
        return None


class FakeHazardClassRepository:
    def get_class_info(self, hazard_class: str):
        return None


class FakeCountryRestrictionsRepository:
    """Fake with canned country data, mirroring real country_restrictions.json shape."""

    def get_restrictions(self, country: str):
        data = {
            "iran": {
                "requires_license_for_all": True,
                "restriction_note": "Comprehensive sanctions apply.",
                "restricted_hazard_classes": [],
                "restricted_keywords": [],
            },
            "russia": {
                "requires_license_for_all": False,
                "restriction_note": "Sectoral sanctions on dual-use goods.",
                "restricted_hazard_classes": [],
                "restricted_keywords": ["batter"],
            },
        }
        return data.get(country.strip().lower())


class TestDestinationAwareComplianceIsolated:
    """Unit tests for the destination-restriction logic using fake repositories."""

    def _make_service(self) -> ComplianceService:
        return ComplianceService(
            restricted_products_repository=FakeRestrictedProductsRepository(),
            hazard_class_repository=FakeHazardClassRepository(),
            country_restrictions_repository=FakeCountryRestrictionsRepository(),
        )

    def test_comprehensive_restriction_country_flags_any_product(self) -> None:
        service = self._make_service()
        response = service.check(
            ComplianceCheckRequest(product_description="cotton t-shirt", destination_country="Iran")
        )
        assert response.destination_restricted is True
        assert "sanctions" in response.destination_notes.lower()

    def test_keyword_match_flags_restricted_destination(self) -> None:
        service = self._make_service()
        response = service.check(
            ComplianceCheckRequest(product_description="lithium battery pack", destination_country="Russia")
        )
        assert response.destination_restricted is True

    def test_unlisted_destination_country_is_not_restricted_but_notes_gap(self) -> None:
        service = self._make_service()
        response = service.check(
            ComplianceCheckRequest(product_description="lithium battery pack", destination_country="Germany")
        )
        assert response.destination_restricted is False
        assert "no specific restriction data" in response.destination_notes.lower()

    def test_no_destination_provided_preserves_old_behavior(self) -> None:
        service = self._make_service()
        response = service.check(
            ComplianceCheckRequest(product_description="lithium battery pack")
        )
        assert response.destination_country is None
        assert response.destination_restricted is False
        assert response.destination_notes is None

    def test_batch_forwards_destination_to_every_item(self) -> None:
        service = self._make_service()
        request = BatchComplianceCheckRequest(
            product_descriptions=["lithium battery pack", "cotton t-shirt"],
            destination_country="Iran",
        )
        response = service.check_batch(request)
        assert all(r.destination_restricted for r in response.results)


class TestCheckProductComplianceToolDestinationIntegration:
    """Integration tests against the real container and real country_restrictions.json."""

    def test_lithium_batteries_to_iran_is_restricted(self) -> None:
        response = server.check_product_compliance("lithium batteries", destination_country="Iran")
        assert response.destination_restricted is True

    def test_lithium_batteries_to_unlisted_country_is_not_restricted(self) -> None:
        response = server.check_product_compliance("lithium batteries", destination_country="Germany")
        assert response.destination_restricted is False