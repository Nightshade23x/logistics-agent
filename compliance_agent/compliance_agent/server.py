"""Entry point for the Compliance Agent MCP server.

Run with:
    python -m compliance_agent.server
from inside the outer compliance_agent/ directory.
"""

from mcp.server.fastmcp import FastMCP

from .container import build_container
from .schemas.compliance import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    BatchComplianceCheckRequest,
    BatchComplianceCheckResponse,
)
from .schemas.hazard_class import HazardClassInfoRequest, HazardClassInfoResponse
from .schemas.agent_response import AgentResponse

mcp = FastMCP("Compliance Agent")
container = build_container()


@mcp.tool()
def get_hazard_class_info(hazard_class: str) -> HazardClassInfoResponse:
    """Look up reference details for an IMDG hazard class number.

    Returns the name, description, and example products for one of the
    9 official IMDG hazard classes (e.g. Class 9: Miscellaneous
    Dangerous Substances and Articles).

    Args:
        hazard_class: The hazard class number to look up, e.g. "9".

    Returns:
        A structured hazard class info result. If the number isn't a
        recognized IMDG class, found will be False.
    """
    request = HazardClassInfoRequest(hazard_class=hazard_class)
    return container.hazard_class_service.get_info(request)


@mcp.tool()
def check_product_compliance(product_description: str) -> ComplianceCheckResponse:
    """Check whether a product is allowed, restricted, or prohibited for trade.

    Looks up the product against a reference dataset of known trade
    compliance rules (based on official IMDG/UN hazardous goods
    classifications) and reports its status along with the reason,
    responsible government department, and any required permits,
    licenses, or certificates.

    Args:
        product_description: Free-text description of the product to check.

    Returns:
        A structured compliance check result. If the product isn't found
        in the reference dataset, status will be "unknown" (this does
        not mean the product is confirmed safe to trade).
    """
    request = ComplianceCheckRequest(product_description=product_description)
    return container.compliance_service.check(request)


@mcp.tool()
def batch_check_compliance(product_descriptions: list[str]) -> BatchComplianceCheckResponse:
    """Check compliance status for multiple products at once, e.g. a shipment manifest.

    Applies the same lookup as check_product_compliance to each product in
    the list, and returns a combined result with summary counts.

    Args:
        product_descriptions: List of free-text product descriptions to check.

    Returns:
        A BatchComplianceCheckResponse with one result per input product,
        in the same order, plus counts of restricted/prohibited/unknown items.
    """
    request = BatchComplianceCheckRequest(product_descriptions=product_descriptions)
    return container.compliance_service.check_batch(request)

@mcp.tool()
def check_product_compliance(
    product_description: str, destination_country: str | None = None
) -> ComplianceCheckResponse:
    """... (existing docstring, add a line about destination_country) ..."""
    request = ComplianceCheckRequest(
        product_description=product_description, destination_country=destination_country
    )
    return container.compliance_service.check(request)


@mcp.tool()
def batch_check_compliance(
    product_descriptions: list[str], destination_country: str | None = None
) -> BatchComplianceCheckResponse:
    """... (existing docstring) ..."""
    request = BatchComplianceCheckRequest(
        product_descriptions=product_descriptions, destination_country=destination_country
    )
    return container.compliance_service.check_batch(request)

@mcp.tool()
def assess_compliance(
    product_description: str, destination_country: str | None = None
) -> AgentResponse:
    """Run a full compliance assessment in the standard agent contract format.

    Same underlying checks as check_product_compliance, wrapped in the
    standard response contract for orchestration by the User Agent.

    Args:
        product_description: Free-text description of the product.
        destination_country: Optional destination country for the shipment.

    Returns:
        A standard AgentResponse with summary, report, and handoff data.
    """
    return container.compliance_assessment_service.assess(product_description, destination_country)

if __name__ == "__main__":
    mcp.run()