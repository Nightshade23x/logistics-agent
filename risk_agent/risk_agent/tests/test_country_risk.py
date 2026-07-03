"""Tests for get_country_risk_score: service isolation + tool integration."""

from ..schemas.country_risk import CountryRiskRequest
from ..services.country_risk_service import CountryRiskService
from .. import server


class FakeCountryRiskRepository:
    """Fake repository implementing CountryRiskRepository's interface for isolated tests."""

    def get_score(self, country: str):
        scores = {"testland": {"country": "Testland", "cpi_score": 85}}
        return scores.get(country.strip().lower())


class TestCountryRiskServiceIsolated:
    """Tests CountryRiskService logic (including tier boundaries) using a fake repository."""

    def test_known_country_returns_score_and_tier(self) -> None:
        service = CountryRiskService(country_risk_repository=FakeCountryRiskRepository())
        response = service.get_risk(CountryRiskRequest(country="Testland"))

        assert response.found is True
        assert response.cpi_score == 85
        assert response.risk_tier == "low"

    def test_unknown_country_returns_not_found(self) -> None:
        service = CountryRiskService(country_risk_repository=FakeCountryRiskRepository())
        response = service.get_risk(CountryRiskRequest(country="Nowhereland"))

        assert response.found is False
        assert response.cpi_score is None
        assert response.risk_tier is None

    def test_tier_boundaries(self) -> None:
        assert CountryRiskService._score_to_tier(70) == "low"
        assert CountryRiskService._score_to_tier(69) == "medium"
        assert CountryRiskService._score_to_tier(50) == "medium"
        assert CountryRiskService._score_to_tier(49) == "high"
        assert CountryRiskService._score_to_tier(30) == "high"
        assert CountryRiskService._score_to_tier(29) == "severe"
        assert CountryRiskService._score_to_tier(0) == "severe"


class TestGetCountryRiskScoreToolIntegration:
    """Integration tests calling the server.py tool function directly with real data."""

    def test_denmark_returns_real_low_risk_data(self) -> None:
        response = server.get_country_risk_score(country="Denmark")

        assert response.found is True
        assert response.cpi_score == 89
        assert response.risk_tier == "low"

    def test_somalia_returns_real_severe_risk_data(self) -> None:
        response = server.get_country_risk_score(country="Somalia")

        assert response.found is True
        assert response.cpi_score == 9
        assert response.risk_tier == "severe"

    def test_unrecognized_country_returns_not_found(self) -> None:
        response = server.get_country_risk_score(country="Wakanda")

        assert response.found is False