"""Pydantic schemas for the get_country_sanctions tool."""

from pydantic import BaseModel, Field


class CountrySanctionsRequest(BaseModel):
    """Input schema for looking up a country's sanctions status."""

    country: str = Field(
        ..., description="Country name to look up, e.g. 'Russia'.", min_length=1
    )


class CountrySanctionsResponse(BaseModel):
    """Output schema for a country sanctions lookup result."""

    country: str = Field(..., description="The original country name that was requested.")
    found: bool = Field(..., description="Whether the country was found in the reference data.")
    sanctions_status: str = Field(
        ...,
        description="Sanctions category, e.g. 'comprehensive_embargo' or 'targeted_sanctions'. "
        "'unknown' if not found.",
    )
    programs: list[str] = Field(
        ...,
        description="Applicable sanctions programs (OFAC, EU, UN, etc.). Empty if not found.",
    )
    notes: str = Field(
        ...,
        description="Additional context on the sanctions regime. Generic message if not found.",
    )
