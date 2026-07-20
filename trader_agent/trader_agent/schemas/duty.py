"""Pydantic schemas for the calculate_duty tool."""

from pydantic import BaseModel, Field


class DutyRequest(BaseModel):
    """Input schema for calculating estimated duty on a shipment."""

    country_from: str = Field(
        ..., description="ISO country name/code of the exporting country.", min_length=1
    )
    country_to: str = Field(
        ..., description="ISO country name/code of the importing country.", min_length=1
    )
    hs_code: str = Field(
        ..., description="The HS code of the product being shipped.", min_length=1
    )


class DutyResponse(BaseModel):
    """Output schema for a duty calculation result."""

    country_from: str = Field(..., description="Exporting country used in the calculation.")
    country_to: str = Field(..., description="Importing country used in the calculation.")
    hs_code: str = Field(..., description="HS code used in the calculation.")
    duty_rate_percent: float = Field(
        ..., description="Estimated duty rate as a percentage of customs value.", ge=0
    )
    rate_source: str = Field(
        ...,
        description="Indicates whether the rate came from an HS-code-specific "
        "override or the default flat rate.",
    )
    message: str = Field(..., description="Human-readable summary of the estimate.")