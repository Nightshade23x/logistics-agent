"""Repository for HS code keyword reference data."""

from .base import load_json_data


class HsCodeRepository:
    """Loads and provides access to HS code keyword mapping data from disk."""

    def __init__(self) -> None:
        """Load the keyword-to-HS-code map from data/hs_codes.json."""
        self._keyword_map: dict[str, str] = load_json_data("hs_codes.json")

    def find_match(self, normalized_description: str) -> tuple[str, str] | None:
        """Find the first keyword that matches within a product description.

        Args:
            normalized_description: The lowercased, stripped product description.

        Returns:
            A tuple of (matched_keyword, hs_code) if a match is found,
            otherwise None.
        """
        for keyword, hs_code in self._keyword_map.items():
            if keyword in normalized_description:
                return keyword, hs_code
        return None