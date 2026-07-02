"""Dependency injection container for the Trader Agent MCP server.

This module is the single place responsible for constructing service
instances. server.py should only ever import from this module, never
directly from the individual service modules.
"""

from .services.incoterms_service import IncotermsService
from .services.hs_code_service import HsCodeService
from .services.duty_service import DutyService
from .services.fta_service import FtaService
from .services.export_strategy_service import ExportStrategyService


class Container:
    """Holds singleton instances of all services used by the MCP server."""

    def __init__(self) -> None:
        """Instantiate all services with no external configuration required."""
        self.incoterms_service: IncotermsService = IncotermsService()
        self.hs_code_service: HsCodeService = HsCodeService()
        self.duty_service: DutyService = DutyService()
        self.fta_service: FtaService = FtaService()
        self.export_strategy_service: ExportStrategyService = ExportStrategyService()


def build_container() -> Container:
    """Factory function that builds and returns a fully wired Container.

    Returns:
        A Container instance with all services instantiated.
    """
    return Container()