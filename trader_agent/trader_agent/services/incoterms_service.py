"""Service responsible for explaining Incoterms (International Commercial Terms)."""


class IncotermsService:
    """Provides explanations for standard Incoterms used in international trade."""

    def __init__(self) -> None:
        """Initialize the IncotermsService with a static reference table.

        No external dependencies or database connections are used; the
        reference data lives in-memory for this initial implementation.
        """
        self._definitions: dict[str, str] = {
            "EXW": "Ex Works: Seller makes goods available at their premises. "
                   "Buyer bears all costs and risks from that point onward.",
            "FOB": "Free On Board: Seller delivers goods on board the vessel "
                   "nominated by the buyer. Risk transfers once goods are on board.",
            "CIF": "Cost, Insurance and Freight: Seller pays for cost, insurance, "
                   "and freight to the named port of destination.",
            "DDP": "Delivered Duty Paid: Seller bears all costs and risks, "
                   "including import duties, until goods reach the buyer.",
            "FCA": "Free Carrier: Seller delivers goods, cleared for export, "
                   "to a carrier nominated by the buyer.",
        }

    def explain(self, term: str) -> str:
        """Return a human-readable explanation of a given Incoterm.

        Args:
            term: The Incoterm code to explain (e.g. "FOB", "CIF").

        Returns:
            A descriptive explanation string. If the term is not recognized,
            a placeholder message is returned instead of raising an error.
        """
        normalized_term = term.strip().upper()
        return self._definitions.get(
            normalized_term,
            f"No definition found for Incoterm '{term}'. "
            f"This is a placeholder response; the term reference table "
            f"will be expanded in a future iteration.",
        )