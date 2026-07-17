"""Repository for country-level corruption risk reference data."""

from .base import load_json_data


class CountryRiskRepository:
    """Loads and provides access to Corruption Perceptions Index (CPI) scores.

    Source: Transparency International's Corruption Perceptions Index (CPI)
    2025, published February 10, 2026. Scores range 0 (highly corrupt) to
    100 (very clean), based on 13 independent expert/business surveys.
    """

    def __init__(self) -> None:
        """Load country risk entries from data/country_risk_index.json."""
        entries = load_json_data("country_risk_index.json")
        # Case-insensitive lookup by country name.
        self._by_country: dict[str, dict] = {
            entry["country"].lower(): entry for entry in entries
        }

    def get_score(self, country: str) -> dict | None:
        """Look up the CPI score entry for a given country name.

        Args:
            country: The country name to look up, e.g. "Brazil".

        Returns:
            A dict with "country" and "cpi_score" if found, otherwise None.
        """
        return self._by_country.get(country.strip().lower())