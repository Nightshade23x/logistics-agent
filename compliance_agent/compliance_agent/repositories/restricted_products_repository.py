"""Repository for restricted/prohibited/allowed product reference data."""

from .base import load_json_data


class RestrictedProductsRepository:
    """Loads and provides access to product compliance reference data from disk."""

    def __init__(self) -> None:
        """Load the product entries from data/restricted_products.json."""
        self._entries: list[dict] = load_json_data("restricted_products.json")

    def find_match(self, normalized_description: str) -> dict | None:
        """Find the first product entry whose keyword appears in the description.

        Args:
            normalized_description: The lowercased, stripped product description.

        Returns:
            The matching product entry dict if found, otherwise None.
        """
        for entry in self._entries:
            for keyword in entry["keywords"]:
                if keyword in normalized_description:
                    return entry
        return None