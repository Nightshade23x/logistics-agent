"""Tests for CountryRiskRepository: direct instantiation, real data lookups."""

from ..repositories.country_risk_repository import CountryRiskRepository


class TestCountryRiskRepository:
    """Tests real data lookups against country_risk_index.json."""

    def test_known_country_returns_score(self) -> None:
        repo = CountryRiskRepository()
        entry = repo.get_score("Denmark")

        assert entry is not None
        assert entry["cpi_score"] == 89

    def test_lookup_is_case_insensitive(self) -> None:
        repo = CountryRiskRepository()
        entry = repo.get_score("denmark")

        assert entry is not None
        assert entry["country"] == "Denmark"

    def test_unknown_country_returns_none(self) -> None:
        repo = CountryRiskRepository()
        entry = repo.get_score("Atlantis")

        assert entry is None