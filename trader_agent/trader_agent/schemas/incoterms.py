"""Pydantic schemas for the explain_incoterm tool."""

from pydantic import BaseModel, Field


class IncotermRequest(BaseModel):
    """Input schema for explaining an Incoterm."""

    term: str = Field(
        ...,
        description="The Incoterm code to explain, e.g. 'FOB', 'CIF', 'EXW'.",
        min_length=1,
    )


class IncotermResponse(BaseModel):
    """Output schema for an Incoterm explanation."""

    term: str = Field(..., description="The normalized Incoterm code that was explained.")
    explanation: str = Field(..., description="Human-readable explanation of the Incoterm.")
    known: bool = Field(
        ..., description="Whether the term was found in the reference table."
    )