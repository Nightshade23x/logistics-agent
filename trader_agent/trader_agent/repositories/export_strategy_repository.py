"""Repository for export strategy market notes reference data."""

from .base import load_json_data


class ExportStrategyRepository:
    """Loads and provides access to market-specific export notes from disk."""

    def __init__(self) -> None:
        """Load market notes from data/export_strategy_notes.json."""
        raw_data: dict = load_json_data("export_strategy_notes.json")
        self._default_note: str = raw_data["default_note"]
        self._market_notes: dict[str, str] = raw_data["market_notes"]

    def get_market_note(self, normalized_market: str) -> str:
        """Return the note for a given target market, or a default note.

        Args:
            normalized_market: The lowercased, stripped target market name.

        Returns:
            The market-specific note if available, otherwise a default note.
        """
        return self._market_notes.get(normalized_market, self._default_note)