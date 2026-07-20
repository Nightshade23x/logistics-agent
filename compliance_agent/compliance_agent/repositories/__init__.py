"""Repository layer for the Compliance Agent MCP server.

Repositories are responsible for loading and providing access to static
reference data (JSON files under data/). Services depend on repositories
rather than reading files or embedding data directly, so the data source
can later be swapped (e.g. for a real regulatory database or API)
without changing service logic.
"""

from .restricted_products_repository import RestrictedProductsRepository
from .hazard_class_repository import HazardClassRepository

__all__ = [
    "RestrictedProductsRepository",
    "HazardClassRepository",
]