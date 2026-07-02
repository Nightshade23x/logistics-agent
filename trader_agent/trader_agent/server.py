"""Entry point for the Trader Agent MCP server.

Run with:
    python -m trader_agent.server
from inside the outer trader_agent/ directory.
"""

from mcp.server.fastmcp import FastMCP

from .container import build_container

mcp = FastMCP("Trader Agent")
container = build_container()


@mcp.tool()
def explain_incoterm(term: str) -> str:
    """Explain the meaning of a given Incoterm.

    Args:
        term: The Incoterm code to explain (e.g. "FOB", "CIF", "EXW").

    Returns:
        A human-readable explanation of the Incoterm.
    """
    return container.incoterms_service.explain(term)


@mcp.tool()
def classify_hs_code(product_description: str) -> str:
    """Classify a product description into an HS (Harmonized System) code.

    Args:
        product_description: Free-text description of the product.

    Returns:
        A best-effort HS code classification for the product.
    """
    return container.hs_code_service.classify(product_description)


@mcp.tool()
def calculate_duty(country_from: str, country_to: str, hs_code: str) -> str:
    """Calculate the estimated duty for a shipment between two countries.

    Args:
        country_from: ISO country name/code of the exporting country.
        country_to: ISO country name/code of the importing country.
        hs_code: The HS code of the product being shipped.

    Returns:
        An estimated duty rate and basis for the shipment.
    """
    return container.duty_service.calculate(country_from, country_to, hs_code)


@mcp.tool()
def suggest_export_strategy(product_description: str, target_market: str) -> str:
    """Suggest an export strategy for a product entering a target market.

    Args:
        product_description: Free-text description of the product.
        target_market: The country or region being targeted for export.

    Returns:
        An export strategy suggestion for the given product and market.
    """
    return container.export_strategy_service.suggest(product_description, target_market)


@mcp.tool()
def check_fta(country_from: str, country_to: str) -> str:
    """Check whether a Free Trade Agreement (FTA) exists between two countries.

    Args:
        country_from: ISO country name/code of the exporting country.
        country_to: ISO country name/code of the importing country.

    Returns:
        A description of any known FTA between the two countries.
    """
    return container.fta_service.check(country_from, country_to)


if __name__ == "__main__":
    mcp.run()