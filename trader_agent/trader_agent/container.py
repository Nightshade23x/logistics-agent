"""Dependency injection container for the Trader Agent MCP server.

This module is the single place responsible for constructing repository
and service instances. server.py should only ever import from this
module, never directly from repositories/ or services/.
"""

from .repositories.incoterms_repository import IncotermsRepository
from .repositories.hs_code_repository import HsCodeRepository
from .repositories.duty_repository import DutyRepository
from .repositories.fta_repository import FtaRepository
from .repositories.export_strategy_repository import ExportStrategyRepository

from .services.incoterms_service import IncotermsService
from .services.hs_code_service import HsCodeService
from .services.duty_service import DutyService
from .services.fta_service import FtaService
from .services.export_strategy_service import ExportStrategyService
from .services.orchestrator_service import OrchestratorService


class Container:
    """Holds singleton instances of all repositories and services."""

    def __init__(self) -> None:
        """Build repositories first, then services, then the orchestrator."""
        incoterms_repository = IncotermsRepository()
        hs_code_repository = HsCodeRepository()
        duty_repository = DutyRepository()
        fta_repository = FtaRepository()
        export_strategy_repository = ExportStrategyRepository()

        self.incoterms_service: IncotermsService = IncotermsService(incoterms_repository)
        self.hs_code_service: HsCodeService = HsCodeService(hs_code_repository)
        self.duty_service: DutyService = DutyService(duty_repository)
        self.fta_service: FtaService = FtaService(fta_repository)
        self.export_strategy_service: ExportStrategyService = ExportStrategyService(
            export_strategy_repository
        )

        # The orchestrator depends on the four services above, not on
        # repositories directly, so it is built last.
        self.orchestrator_service: OrchestratorService = OrchestratorService(
            hs_code_service=self.hs_code_service,
            duty_service=self.duty_service,
            fta_service=self.fta_service,
            export_strategy_service=self.export_strategy_service,
        )


def build_container() -> Container:
    """Factory function that builds and returns a fully wired Container.

    Returns:
        A Container instance with all repositories and services instantiated.
    """
    return Container()