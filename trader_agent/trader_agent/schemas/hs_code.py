"""Pydantic schemas for the classify_hs_code tool."""

from pydantic import BaseModel, Field


class HsCodeRequest(BaseModel):
    """Input schema for classifying a product into an HS code."""

    product_description: str = Field(
        ...,
        description="Free-text description of the product to classify.",
        min_length=1,
    )


class HsCodeResponse(BaseModel):
    """Output schema for an HS code classification result."""

    product_description: str = Field(
        ..., description="The original product description that was classified."
    )
    hs_code: str | None = Field(
        default=None,
        description="The matched HS code, if any was found.",
    )
    matched_keyword: str | None = Field(
        default=None,
        description="The keyword that triggered the match, if any.",
    )
    matched: bool = Field(
        ..., description="Whether a confident keyword match was found."
    )
    message: str = Field(
        ..., description="Human-readable summary of the classification result."
    )