"""Service responsible for checking Free Trade Agreements (FTAs) between countries."""


class FtaService:
    """Provides lookups for known Free Trade Agreements between country pairs.

    This initial implementation uses a small in-memory set of known FTAs.
    Country matching is case-insensitive and order-independent.
    """

    def __init__(self) -> None:
        """Initialize the FtaService with a static set of known FTA pairs."""
        self._known_ftas: dict[frozenset[str], str] = {
            frozenset({"india", "japan"}): "India-Japan CEPA",
            frozenset({"india", "uae"}): "India-UAE CEPA",
            frozenset({"usa", "canada"}): "USMCA",
            frozenset({"usa", "mexico"}): "USMCA",
            frozenset({"canada", "mexico"}): "USMCA",
            frozenset({"uk", "australia"}): "UK-Australia FTA",
            frozenset({"eu", "japan"}): "EU-Japan EPA",
        }

    def check(self, country_from: str, country_to: str) -> str:
        """Check whether a known Free Trade Agreement exists between two countries.

        Args:
            country_from: ISO country name/code of the exporting country.
            country_to: ISO country name/code of the importing country.

        Returns:
            A description of the matching FTA if found, otherwise a
            message indicating no known agreement was found in the
            reference table.
        """
        pair_key = frozenset(
            {country_from.strip().lower(), country_to.strip().lower()}
        )
        agreement_name = self._known_ftas.get(pair_key)

        if agreement_name:
            return (
                f"A Free Trade Agreement exists between {country_from} and "
                f"{country_to}: {agreement_name}. Preferential duty rates "
                f"may apply; verify specific product eligibility and "
                f"rules of origin."
            )

        return (
            f"No known Free Trade Agreement found between {country_from} "
            f"and {country_to} in the current reference table. This does "
            f"not conclusively rule out an agreement; the reference table "
            f"will be expanded in a future iteration."
        )