"""Service responsible for explaining Incoterms (International Commercial Terms)."""

from ..repositories.incoterms_repository import IncotermsRepository
from ..schemas.incoterms import IncotermRequest, IncotermResponse


class IncotermsService:
    """Provides explanations for standard Incoterms used in international trade."""

    def __init__(self, repository: IncotermsRepository) -> None:
        """Initialize the IncotermsService with an injected repository.

        Args:
            repository: Provides access to Incoterms reference data.
        """
        self._repository = repository

    def explain(self, request: IncotermRequest) -> IncotermResponse:
        """Return a structured explanation of a given Incoterm.

        Args:
            request: The validated Incoterm request.

        Returns:
            An IncotermResponse containing the explanation and match status.
        """
        normalized_term = request.term.strip().upper()
        definition = self._repository.get_definition(normalized_term)

        if definition is not None:
            return IncotermResponse(term=normalized_term, explanation=definition, known=True)

        return IncotermResponse(
            term=normalized_term,
            explanation=(
                f"No definition found for Incoterm '{request.term}'. "
                f"This is a placeholder response; the term reference table "
                f"will be expanded in a future iteration."
            ),
            known=False,
        )