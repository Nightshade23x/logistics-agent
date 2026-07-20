"""Repository for IMDG hazard class reference data."""

from .base import load_json_data


class HazardClassRepository:
    """Loads and provides access to the 9 IMDG hazard classes from disk."""

    def __init__(self) -> None:
        """Load hazard class definitions from data/hazard_classes.json."""
        self._classes: dict[str, dict] = load_json_data("hazard_classes.json")

    def get_class_info(self, hazard_class: str) -> dict | None:
        """Look up the name/description/examples for a given hazard class number.

        Args:
            hazard_class: The hazard class number as a string, e.g. "9".

        Returns:
            A dict with "name", "description", and "examples" if found,
            otherwise None.
        """
        return self._classes.get(hazard_class)