"""Entry point for the Compliance Agent MCP server.

Run with:
    python -m compliance_agent.server
from inside the outer compliance_agent/ directory.
"""

from mcp.server.fastmcp import FastMCP

from .container import build_container
from .schemas.compliance import ComplianceCheckRequest, ComplianceCheckResponse
from .schemas.hazard_class import HazardClassInfoRequest, HazardClassInfoResponse

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


if __name__ == "__main__":
    mcp.run()