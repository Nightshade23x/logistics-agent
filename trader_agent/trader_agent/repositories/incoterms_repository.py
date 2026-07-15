"""Repository for Incoterms reference data."""

from .base import load_json_data


class IncotermsRepository:
    """Loads and provides access to Incoterms reference data from disk."""

    def __init__(self) -> None:
        """Load Incoterms definitions from data/incoterms.json."""
        self._definitions: dict[str, str] = load_json_data("incoterms.json")

    def get_definition(self, term: str) -> str | None:
        """Look up the definition for a given Incoterm code.

        Args:
            term: The normalized (uppercase, stripped) Incoterm code.

        Returns:
            The definition string if found, otherwise None.
        """
        return self._definitions.get(term)