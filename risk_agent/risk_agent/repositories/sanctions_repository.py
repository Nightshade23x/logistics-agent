"""Repository for country-level sanctions reference data."""

from .base import load_json_data


class SanctionsRepository:
    """Loads and provides access to sanctions reference data by country."""

    def __init__(self) -> None:
        """Load sanctions entries from data/sanctions_index.json."""
        entries = load_json_data("sanctions_index.json")
        # Case-insensitive lookup by country name.
        self._by_country: dict[str, dict] = {
            entry["country"].lower(): entry for entry in entries
        }

    def get_country(self, country: str) -> dict | None:
        """Look up the sanctions entry for a given country name.

        Args:
            country: The country name to look up, e.g. "Russia".

        Returns:
            A dict with "country", "sanctions_status", "programs", and "notes"
            if found, otherwise None.
        """
        return self._by_country.get(country.strip().lower())
