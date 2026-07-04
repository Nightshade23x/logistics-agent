"""Repository for country-level trade restriction reference data."""

from .base import load_json_data


class CountryRestrictionsRepository:
    """Loads and provides access to country-level trade restrictions."""

    def __init__(self) -> None:
        """Load country restriction entries from data/country_restrictions.json."""
        entries = load_json_data("country_restrictions.json")
        self._by_country: dict[str, dict] = {
            entry["country"].lower(): entry for entry in entries
        }

    def get_restrictions(self, country: str) -> dict | None:
        """Look up restriction data for a destination country.

        Args:
            country: The destination country name, e.g. "Iran".

        Returns:
            A dict with restriction fields if found, otherwise None
            (meaning no known country-specific restrictions on file —
            NOT confirmation the destination is unrestricted).
        """
        return self._by_country.get(country.strip().lower())