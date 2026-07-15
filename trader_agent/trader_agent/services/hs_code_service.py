"""Service responsible for classifying products into HS (Harmonized System) codes."""

from ..repositories.hs_code_repository import HsCodeRepository
from ..schemas.hs_code import HsCodeRequest, HsCodeResponse


class HsCodeService:
    """Provides HS code classification for product descriptions."""

    def __init__(self, repository: HsCodeRepository) -> None:
        """Initialize the HsCodeService with an injected repository.

        Args:
            repository: Provides access to HS code keyword reference data.
        """
        self._repository = repository

    def classify(self, request: HsCodeRequest) -> HsCodeResponse:
        """Classify a product description into an approximate HS code.

        Args:
            request: The validated HS code classification request.

        Returns:
            An HsCodeResponse describing the classification result.
        """
        normalized_description = request.product_description.strip().lower()
        match = self._repository.find_match(normalized_description)

        if match is not None:
            matched_keyword, hs_code = match
            return HsCodeResponse(
                product_description=request.product_description,
                hs_code=hs_code,
                matched_keyword=matched_keyword,
                matched=True,
                message=(
                    f"Estimated HS code for '{request.product_description}': "
                    f"{hs_code} (matched keyword: '{matched_keyword}'). This is a "
                    f"best-effort classification and should be verified against "
                    f"official customs tariff schedules."
                ),
            )

        return HsCodeResponse(
            product_description=request.product_description,
            hs_code=None,
            matched_keyword=None,
            matched=False,
            message=(
                f"No HS code match found for '{request.product_description}'. "
                f"This is a placeholder response; a more comprehensive "
                f"classification model will be added in a future iteration."
            ),
        )