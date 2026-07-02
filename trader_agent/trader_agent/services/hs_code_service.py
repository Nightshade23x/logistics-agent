"""Service responsible for classifying products into HS (Harmonized System) codes."""


class HsCodeService:
    """Provides HS code classification for product descriptions.

    This initial implementation uses simple keyword matching against a
    small in-memory reference table. It is intended to be replaced or
    augmented with a more robust classification approach later.
    """

    def __init__(self) -> None:
        """Initialize the HsCodeService with a static keyword-to-HS-code table."""
        self._keyword_map: dict[str, str] = {
            "laptop": "8471.30",
            "computer": "8471.30",
            "phone": "8517.13",
            "smartphone": "8517.13",
            "shirt": "6109.10",
            "t-shirt": "6109.10",
            "shoe": "6403.99",
            "shoes": "6403.99",
            "chair": "9401.61",
            "furniture": "9403.60",
            "coffee": "0901.21",
            "tea": "0902.30",
            "toy": "9503.00",
        }

    def classify(self, product_description: str) -> str:
        """Classify a product description into an approximate HS code.

        Args:
            product_description: Free-text description of the product.

        Returns:
            A best-effort HS code classification, or a placeholder message
            if no keyword match is found in the reference table.
        """
        normalized_description = product_description.strip().lower()

        for keyword, hs_code in self._keyword_map.items():
            if keyword in normalized_description:
                return (
                    f"Estimated HS code for '{product_description}': {hs_code} "
                    f"(matched keyword: '{keyword}'). This is a best-effort "
                    f"classification and should be verified against official "
                    f"customs tariff schedules."
                )

        return (
            f"No HS code match found for '{product_description}'. "
            f"This is a placeholder response; a more comprehensive "
            f"classification model will be added in a future iteration."
        )