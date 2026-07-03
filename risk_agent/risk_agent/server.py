"""Entry point for the Risk Agent MCP server.

Run with:
    python -m risk_agent.server
from inside the outer risk_agent/ directory.
"""

from mcp.server.fastmcp import FastMCP

from .container import build_container
from .schemas.country_risk import CountryRiskRequest, CountryRiskResponse

mcp = FastMCP("Risk Agent")
container = build_container()


@mcp.tool()
def get_country_risk_score(country: str) -> CountryRiskResponse:
    """Look up a country's corruption risk score for trade risk assessment.

    Returns the Corruption Perceptions Index (CPI) score for the given
    country, per Transparency International's CPI 2025, along with a
    simplified risk tier (low/medium/high/severe) for quick reference.

    Args:
        country: The country name to look up, e.g. "Brazil".

    Returns:
        A structured country risk result. If the country isn't in the
        reference dataset, found will be False.
    """
    request = CountryRiskRequest(country=country)
    return container.country_risk_service.get_risk(request)


if __name__ == "__main__":
    mcp.run()