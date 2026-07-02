"""Pydantic schemas for the suggest_export_strategy tool."""

from pydantic import BaseModel, Field


class ExportStrategyRequest(BaseModel):
    """Input schema for requesting an export strategy suggestion."""

    product_description: str = Field(
        ..., description="Free-text description of the product.", min_length=1
    )
    target_market: str = Field(
        ...,
        description="The country or region being targeted for export.",
        min_length=1,
    )


class ExportStrategyResponse(BaseModel):
    """Output schema for an export strategy suggestion."""

    product_description: str = Field(
        ..., description="The product description used in the suggestion."
    )
    target_market: str = Field(
        ..., description="The target market used in the suggestion."
    )
    market_note: str = Field(
        ..., description="Market-specific guidance, if available for this market."
    )
    strategy: str = Field(
        ..., description="The full export strategy suggestion text."
    )