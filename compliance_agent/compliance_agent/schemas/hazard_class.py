"""Pydantic schemas for the get_hazard_class_info tool."""

from pydantic import BaseModel, Field


class HazardClassInfoRequest(BaseModel):
    """Input schema for looking up an IMDG hazard class by number."""

    hazard_class: str = Field(
        ..., description="The IMDG hazard class number to look up, e.g. '9'.", min_length=1
    )


class HazardClassInfoResponse(BaseModel):
    """Output schema for an IMDG hazard class lookup result."""

    hazard_class: str = Field(
        ..., description="The original hazard class number that was requested."
    )
    found: bool = Field(
        ..., description="Whether the hazard class number matched a known IMDG class."
    )
    name: str | None = Field(
        default=None, description="The human-readable name of the hazard class, if found."
    )
    description: str | None = Field(
        default=None, description="Description of what this hazard class covers, if found."
    )
    examples: list[str] = Field(
        default_factory=list, description="Example products in this hazard class, if found."
    )