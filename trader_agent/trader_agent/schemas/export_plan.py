"""Pydantic schemas for the plan_export orchestrator tool."""

from pydantic import BaseModel, Field

from .hs_code import HsCodeResponse
from .duty import DutyResponse
from .fta import FtaResponse
from .export_strategy import ExportStrategyResponse


class ExportPlanRequest(BaseModel):
    """Input schema for requesting a full export plan.

    Combines the inputs needed to run HS code classification, duty
    calculation, FTA lookup, and export strategy suggestion as one
    coordinated workflow.
    """

    product_description: str = Field(
        ..., description="Free-text description of the product.", min_length=1
    )
    country_from: str = Field(
        ..., description="ISO country name/code of the exporting country.", min_length=1
    )
    country_to: str = Field(
        ..., description="ISO country name/code of the importing country.", min_length=1
    )
    target_market: str = Field(
        ...,
        description="The country or region being targeted for export "
        "(often the same as country_to).",
        min_length=1,
    )


class ExportPlanResponse(BaseModel):
    """Output schema for a full export plan.

    Contains the individual results from each step of the workflow,
    plus a top-level summary tying them together.
    """

    hs_code_result: HsCodeResponse = Field(
        ..., description="Result of classifying the product into an HS code."
    )
    duty_result: DutyResponse = Field(
        ..., description="Result of estimating the duty for the shipment."
    )
    fta_result: FtaResponse = Field(
        ..., description="Result of checking for an applicable FTA."
    )
    export_strategy_result: ExportStrategyResponse = Field(
        ..., description="Result of suggesting an export strategy."
    )
    summary: str = Field(
        ..., description="A concise, human-readable summary tying all four results together."
    )