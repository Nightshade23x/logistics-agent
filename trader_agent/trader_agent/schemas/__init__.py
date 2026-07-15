"""Pydantic schemas for the Trader Agent MCP server.

Each module here defines the Request/Response schema pair for one tool.
This __init__.py re-exports all schemas so they can be imported either
from the specific module (e.g. `from .schemas.incoterms import ...`) or
from the package root (e.g. `from .schemas import IncotermRequest`).
"""

from .incoterms import IncotermRequest, IncotermResponse
from .hs_code import HsCodeRequest, HsCodeResponse
from .duty import DutyRequest, DutyResponse
from .fta import FtaRequest, FtaResponse
from .export_strategy import ExportStrategyRequest, ExportStrategyResponse

__all__ = [
    "IncotermRequest",
    "IncotermResponse",
    "HsCodeRequest",
    "HsCodeResponse",
    "DutyRequest",
    "DutyResponse",
    "FtaRequest",
    "FtaResponse",
    "ExportStrategyRequest",
    "ExportStrategyResponse",
]