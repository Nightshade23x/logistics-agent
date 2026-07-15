"""Repository for Free Trade Agreement (FTA) reference data."""

from .base import load_json_data


class FtaRepository:
    """Loads and provides access to FTA reference data from disk."""

    def __init__(self) -> None:
        """Load known FTA country pairs from data/fta_agreements.json."""
        raw_entries: list[dict] = load_json_data("fta_agreements.json")
        self._agreements: dict[frozenset[str], str] = {
            frozenset(entry["countries"]): entry["agreement_name"]
            for entry in raw_entries
        }

    def find_agreement(self, country_a: str, country_b: str) -> str | None:
        """Look up a known FTA between two countries, order-independent.

        Args:
            country_a: The first country (lowercased, stripped).
            country_b: The second country (lowercased, stripped).

        Returns:
            The agreement name if a match is found, otherwise None.
        """
        pair_key = frozenset({country_a, country_b})
        return self._agreements.get(pair_key)