"""Repository layer for the Trader Agent MCP server.

Repositories are responsible for loading and providing access to static
reference data (currently JSON files under data/). Services depend on
repositories rather than reading files or embedding data directly, so
the data source can later be swapped (e.g. for a database or external
API) without changing service logic.
"""

from .incoterms_repository import IncotermsRepository
from .hs_code_repository import HsCodeRepository
from .duty_repository import DutyRepository
from .fta_repository import FtaRepository
from .export_strategy_repository import ExportStrategyRepository

__all__ = [
    "IncotermsRepository",
    "HsCodeRepository",
    "DutyRepository",
    "FtaRepository",
    "ExportStrategyRepository",
]