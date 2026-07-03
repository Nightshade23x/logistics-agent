"""Entry point for the Trader Agent MCP server.

Run with:
    python -m trader_agent.server
from inside the outer trader_agent/ directory.
"""

from mcp.server.fastmcp import FastMCP

from .container import build_container
from .schemas import (
    IncotermRequest,
    IncotermResponse,
    HsCodeRequest,
    HsCodeResponse,
    DutyRequest,
    DutyResponse,
    FtaRequest,
    FtaResponse,
    ExportStrategyRequest,
    ExportStrategyResponse,
)
from .schemas.export_plan import ExportPlanRequest, ExportPlanResponse

mcp = FastMCP("Trader Agent")
container = build_container()


@mcp.tool()
def explain_incoterm(term: str) -> IncotermResponse:
    """Explain the meaning of a given Incoterm.

    Args:
        term: The Incoterm code to explain (e.g. "FOB", "CIF", "EXW").

    Returns:
        A structured explanation of the Incoterm.
    """
    request = IncotermRequest(term=term)
    return container.incoterms_service.explain(request)


@mcp.tool()
def classify_hs_code(product_description: str) -> HsCodeResponse:
    """Classify a product description into an HS (Harmonized System) code.

    Args:
        product_description: Free-text description of the product.

    Returns:
        A structured best-effort HS code classification for the product.
    """
    request = HsCodeRequest(product_description=product_description)
    return container.hs_code_service.classify(request)


@mcp.tool()
def calculate_duty(country_from: str, country_to: str, hs_code: str) -> DutyResponse:
    """Calculate the estimated duty for a shipment between two countries.

    Args:
        country_from: ISO country name/code of the exporting country.
        country_to: ISO country name/code of the importing country.
        hs_code: The HS code of the product being shipped.

    Returns:
        A structured estimated duty rate and basis for the shipment.
    """
    request = DutyRequest(country_from=country_from, country_to=country_to, hs_code=hs_code)
    return container.duty_service.calculate(request)


@mcp.tool()
def suggest_export_strategy(
    product_description: str, target_market: str
) -> ExportStrategyResponse:
    """Suggest an export strategy for a product entering a target market.

    Args:
        product_description: Free-text description of the product.
        target_market: The country or region being targeted for export.

    Returns:
        A structured export strategy suggestion for the given product and market.
    """
    request = ExportStrategyRequest(
        product_description=product_description, target_market=target_market
    )
    return container.export_strategy_service.suggest(request)


@mcp.tool()
def check_fta(country_from: str, country_to: str) -> FtaResponse:
    """Check whether a Free Trade Agreement (FTA) exists between two countries.

    Args:
        country_from: ISO country name/code of the exporting country.
        country_to: ISO country name/code of the importing country.

    Returns:
        A structured description of any known FTA between the two countries.
    """
    request = FtaRequest(country_from=country_from, country_to=country_to)
    return container.fta_service.check(request)

@mcp.tool()
def plan_export(
    product_description: str, country_from: str, country_to: str, target_market: str
) -> ExportPlanResponse:
    """Run a full export-planning workflow for a product and market.

    Chains together HS code classification, duty estimation, an FTA
    check, and an export strategy suggestion into a single coordinated
    result, so the agent can reason about a shipment end to end in one
    call instead of four separate ones.

    Args:
        product_description: Free-text description of the product.
        country_from: ISO country name/code of the exporting country.
        country_to: ISO country name/code of the importing country.
        target_market: The country or region being targeted for export
            (often the same as country_to).

    Returns:
        A structured export plan combining all four step results plus
        an overall summary.
    """
    request = ExportPlanRequest(
        product_description=product_description,
        country_from=country_from,
        country_to=country_to,
        target_market=target_market,
    )
    return container.orchestrator_service.plan(request)

if __name__ == "__main__":
    mcp.run()