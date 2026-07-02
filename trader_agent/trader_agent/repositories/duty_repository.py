"""Repository for duty rate reference data."""

from .base import load_json_data


class DutyRepository:
    """Loads and provides access to duty rate reference data from disk."""

    def __init__(self) -> None:
        """Load default and HS-code-specific duty rates from data/duty_rates.json."""
        raw_data: dict = load_json_data("duty_rates.json")
        self._default_rate_percent: float = raw_data["default_rate_percent"]
        self._hs_code_overrides: dict[str, float] = raw_data["hs_code_overrides"]

    def get_default_rate(self) -> float:
        """Return the default flat duty rate percentage used when no override applies."""
        return self._default_rate_percent

    def get_override_rate(self, hs_code: str) -> float | None:
        """Look up an HS-code-specific duty rate override.

        Args:
            hs_code: The stripped HS code to look up.

        Returns:
            The override rate percentage if one exists, otherwise None.
        """
        return self._hs_code_overrides.get(hs_code)