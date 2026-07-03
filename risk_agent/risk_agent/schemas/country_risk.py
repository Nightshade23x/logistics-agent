"""Pydantic schemas for the get_country_risk_score tool."""

from pydantic import BaseModel, Field


class CountryRiskRequest(BaseModel):
    """Input schema for looking up a country's corruption risk score."""

    country: str = Field(
        ..., description="Country name to look up, e.g. 'Brazil'.", min_length=1
    )


class CountryRiskResponse(BaseModel):
    """Output schema for a country risk lookup result."""

    country: str = Field(..., description="The original country name that was requested.")
    found: bool = Field(..., description="Whether the country was found in the reference data.")
    cpi_score: int | None = Field(
        default=None,
        description="Corruption Perceptions Index score, 0 (highly corrupt) to 100 "
        "(very clean), per Transparency International CPI 2025. None if not found.",
    )
    risk_tier: str | None = Field(
        default=None,
        description="Risk tier derived from cpi_score: 'low' (70-100), 'medium' (50-69), "
        "'high' (30-49), or 'severe' (0-29). This bucketing is a simplification for "
        "quick reference, not an official Transparency International classification. "
        "None if not found.",
    )
    source: str = Field(
        default="Transparency International Corruption Perceptions Index (CPI) 2025",
        description="Data source citation for the score.",
    )