"""Pydantic schemas for the check_fta tool."""

from pydantic import BaseModel, Field


class FtaRequest(BaseModel):
    """Input schema for checking a Free Trade Agreement between two countries."""

    country_from: str = Field(
        ..., description="ISO country name/code of the exporting country.", min_length=1
    )
    country_to: str = Field(
        ..., description="ISO country name/code of the importing country.", min_length=1
    )


class FtaResponse(BaseModel):
    """Output schema for an FTA check result."""

    country_from: str = Field(..., description="Exporting country used in the lookup.")
    country_to: str = Field(..., description="Importing country used in the lookup.")
    fta_exists: bool = Field(
        ..., description="Whether a known Free Trade Agreement was found."
    )
    agreement_name: str | None = Field(
        default=None, description="Name of the matching agreement, if found."
    )
    message: str = Field(..., description="Human-readable summary of the lookup result.")