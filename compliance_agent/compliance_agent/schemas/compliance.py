"""Pydantic schemas for compliance-related tools."""

from pydantic import BaseModel, Field


class ComplianceCheckRequest(BaseModel):
    """Input schema for checking a product's trade compliance status."""

    product_description: str = Field(
        ..., description="Free-text description of the product to check.", min_length=1
    )


class ComplianceCheckResponse(BaseModel):
    """Output schema for a product compliance check result."""

    product_description: str = Field(
        ..., description="The original product description that was checked."
    )
    matched: bool = Field(
        ..., description="Whether a confident keyword match was found in the reference data."
    )
    matched_product: str | None = Field(
        default=None, description="The canonical product name that was matched, if any."
    )
    status: str = Field(
        ...,
        description="Compliance status: 'allowed', 'restricted', 'prohibited', "
        "or 'unknown' if no match was found.",
    )
    hazard_class: str | None = Field(
        default=None, description="The IMDG hazard class number, if applicable."
    )
    hazard_class_name: str | None = Field(
        default=None, description="The human-readable name of the hazard class, if applicable."
    )
    un_numbers: list[str] = Field(
        default_factory=list, description="Relevant UN numbers for this product, if any."
    )
    reason: str = Field(
        ..., description="Explanation of why the product has this compliance status."
    )
    responsible_department: str | None = Field(
        default=None,
        description="The government department or regulatory body responsible for this product.",
    )
    required_permits: list[str] = Field(
        default_factory=list, description="Permits required to trade this product, if any."
    )
    required_licenses: list[str] = Field(
        default_factory=list, description="Licenses required to trade this product, if any."
    )
    required_certificates: list[str] = Field(
        default_factory=list,
        description="Certificates or test reports required to trade this product, if any.",
    )
    notes: str | None = Field(
        default=None, description="Additional practical notes about handling this product."
    )


class BatchComplianceCheckRequest(BaseModel):
    """Input schema for checking multiple products' trade compliance status at once."""

    product_descriptions: list[str] = Field(
        ...,
        description="List of free-text product descriptions to check, e.g. a shipment manifest.",
        min_length=1,
    )


class BatchComplianceCheckResponse(BaseModel):
    """Output schema for a batch compliance check result."""

    results: list[ComplianceCheckResponse] = Field(
        ..., description="One compliance check result per input product description, in order."
    )
    restricted_count: int = Field(
        ..., description="Number of products with status 'restricted'."
    )
    prohibited_count: int = Field(
        ..., description="Number of products with status 'prohibited'."
    )
    unknown_count: int = Field(
        ..., description="Number of products with status 'unknown' (not found in reference data)."
    )