"""Service responsible for suggesting export strategies for products entering target markets."""

from ..repositories.export_strategy_repository import ExportStrategyRepository
from ..schemas.export_strategy import ExportStrategyRequest, ExportStrategyResponse


class ExportStrategyService:
    """Provides high-level export strategy suggestions."""

    def __init__(self, repository: ExportStrategyRepository) -> None:
        """Initialize the ExportStrategyService with an injected repository.

        Args:
            repository: Provides access to market-specific export notes.
        """
        self._repository = repository

    def suggest(self, request: ExportStrategyRequest) -> ExportStrategyResponse:
        """Suggest an export strategy for a product entering a target market.

        Args:
            request: The validated export strategy request.

        Returns:
            An ExportStrategyResponse containing the suggestion.
        """
        normalized_market = request.target_market.strip().lower()
        market_note = self._repository.get_market_note(normalized_market)

        strategy_text = (
            f"Export strategy suggestion for '{request.product_description}' "
            f"targeting {request.target_market}: Start by confirming HS code "
            f"classification and applicable duties, then verify FTA eligibility. "
            f"Market-specific note: {market_note}"
        )

        return ExportStrategyResponse(
            product_description=request.product_description,
            target_market=request.target_market,
            market_note=market_note,
            strategy=strategy_text,
        )