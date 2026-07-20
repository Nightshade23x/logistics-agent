"""Tests for get_country_sanctions: service isolation + tool integration."""

from ..schemas.sanctions import CountrySanctionsRequest
from ..services.sanctions_service import SanctionsService
from .. import server


class FakeSanctionsRepository:
    """Fake repository implementing SanctionsRepository's interface for isolated tests."""

    def get_country(self, country: str):
        records = {
            "testland": {
                "country": "Testland",
                "sanctions_status": "targeted_sanctions",
                "programs": ["OFAC - Testland Sanctions"],
                "notes": "Test sanctions note.",
            }
        }
        return records.get(country.strip().lower())


class TestSanctionsServiceIsolated:
    """Tests SanctionsService logic using a fake repository."""

    def test_known_country_returns_sanctions_data(self) -> None:
        service = SanctionsService(sanctions_repository=FakeSanctionsRepository())
        response = service.get_country(CountrySanctionsRequest(country="Testland"))

        assert response.found is True
        assert response.sanctions_status == "targeted_sanctions"
        assert response.programs == ["OFAC - Testland Sanctions"]
        assert response.notes == "Test sanctions note."

    def test_unknown_country_returns_not_found(self) -> None:
        service = SanctionsService(sanctions_repository=FakeSanctionsRepository())
        response = service.get_country(CountrySanctionsRequest(country="Nowhereland"))

        assert response.found is False
        assert response.sanctions_status == "unknown"
        assert response.programs == []
        assert response.notes == "No sanctions information available."


class TestGetCountrySanctionsToolIntegration:
    """Integration tests calling the server.py tool function directly with real data."""

    def test_russia_returns_real_targeted_sanctions_data(self) -> None:
        response = server.get_country_sanctions(country="Russia")

        assert response.found is True
        assert response.sanctions_status == "targeted_sanctions"
        assert len(response.programs) >= 1

    def test_cuba_returns_real_comprehensive_embargo_data(self) -> None:
        response = server.get_country_sanctions(country="Cuba")

        assert response.found is True
        assert response.sanctions_status == "comprehensive_embargo"

    def test_unrecognized_country_returns_not_found(self) -> None:
        response = server.get_country_sanctions(country="Wakanda")

        assert response.found is False
        assert response.sanctions_status == "unknown"
