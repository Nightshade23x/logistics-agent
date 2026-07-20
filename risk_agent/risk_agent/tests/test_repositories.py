"""Tests for repository classes: direct instantiation, real data lookups."""

from ..repositories.country_risk_repository import CountryRiskRepository
from ..repositories.sanctions_repository import SanctionsRepository


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


class TestSanctionsRepository:
    """Tests real data lookups against sanctions_index.json."""

    def test_known_country_returns_sanctions_data(self) -> None:
        repo = SanctionsRepository()
        entry = repo.get_country("Russia")

        assert entry is not None
        assert entry["sanctions_status"] == "targeted_sanctions"
        assert "OFAC - Russia Harmful Foreign Activities Sanctions" in entry["programs"]

    def test_lookup_is_case_insensitive(self) -> None:
        repo = SanctionsRepository()
        entry = repo.get_country("cuba")

        assert entry is not None
        assert entry["country"] == "Cuba"
        assert entry["sanctions_status"] == "comprehensive_embargo"

    def test_unknown_country_returns_none(self) -> None:
        repo = SanctionsRepository()
        entry = repo.get_country("Atlantis")

        assert entry is None
