"""Tests for the batch_check_compliance tool: service isolation + tool integration."""

from ..schemas.compliance import BatchComplianceCheckRequest
from ..services.compliance_service import ComplianceService
from .. import server


class FakeRestrictedProductsRepository:
    """Fake repository returning canned matches for isolated batch tests."""

    def find_match(self, normalized_description: str):
        if "battery" in normalized_description or "batter" in normalized_description:
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
        if "ammunition" in normalized_description:
            return {
                "product": "Small arms ammunition",
                "status": "prohibited",
                "hazard_class": "1",
                "un_numbers": ["UN0012"],
                "reason": "Explosive projection hazard.",
                "responsible_department": "Defense authority",
                "required_permits": [],
                "required_licenses": [],
                "required_certificates": [],
                "notes": None,
            }
        return None


class FakeHazardClassRepository:
    """Fake repository returning no hazard class detail (not exercised in these tests)."""

    def get_class_info(self, hazard_class: str):
        return None

class FakeCountryRestrictionsRepository:
    """Fake with no restrictions data, for isolated service tests."""

    def get_restrictions(self, country: str) -> dict | None:
        return None

class TestComplianceServiceBatchIsolated:
    """Tests ComplianceService.check_batch logic using fake repositories."""

    def test_batch_counts_are_correct(self) -> None:
        service = ComplianceService(
            restricted_products_repository=FakeRestrictedProductsRepository(),
            hazard_class_repository=FakeHazardClassRepository(),
            country_restrictions_repository=FakeCountryRestrictionsRepository(),

        )
        request = BatchComplianceCheckRequest(
            product_descriptions=["lithium battery pack", "ammunition rounds", "a plain t-shirt"]
        )
        response = service.check_batch(request)

        assert len(response.results) == 3
        assert response.restricted_count == 1
        assert response.prohibited_count == 1
        assert response.unknown_count == 1
        assert response.results[0].status == "restricted"
        assert response.results[1].status == "prohibited"
        assert response.results[2].status == "unknown"

    def test_batch_preserves_input_order(self) -> None:
        service = ComplianceService(
            restricted_products_repository=FakeRestrictedProductsRepository(),
            hazard_class_repository=FakeHazardClassRepository(),
            country_restrictions_repository=FakeCountryRestrictionsRepository(),

        )
        request = BatchComplianceCheckRequest(
            product_descriptions=["ammunition", "lithium battery"]
        )
        response = service.check_batch(request)

        assert response.results[0].status == "prohibited"
        assert response.results[1].status == "restricted"


class TestBatchCheckComplianceToolIntegration:
    """Integration tests calling the server.py tool function directly with real data."""

    def test_mixed_manifest_returns_correct_summary(self) -> None:
        response = server.batch_check_compliance(
            product_descriptions=[
                "lithium batteries for a laptop",
                "ammunition rounds",
                "a plain t-shirt",
                "a bottle of perfume",
            ]
        )

        assert len(response.results) == 4
        assert response.restricted_count == 2  # batteries + perfume
        assert response.prohibited_count == 1  # ammunition
        assert response.unknown_count == 0
        assert response.results[2].status == "allowed"

    def test_empty_list_is_rejected_by_schema(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            from ..schemas.compliance import BatchComplianceCheckRequest
            BatchComplianceCheckRequest(product_descriptions=[])


