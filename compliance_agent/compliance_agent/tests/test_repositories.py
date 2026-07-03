"""Unit tests for the Compliance Agent repository layer."""

from ..repositories.restricted_products_repository import RestrictedProductsRepository
from ..repositories.hazard_class_repository import HazardClassRepository


class TestRestrictedProductsRepository:
    """Tests for RestrictedProductsRepository."""

    def test_known_keyword_returns_match(self) -> None:
        repository = RestrictedProductsRepository()
        entry = repository.find_match("lithium batteries")
        assert entry is not None
        assert entry["status"] == "restricted"
        assert "UN3480" in entry["un_numbers"]

    def test_unknown_description_returns_none(self) -> None:
        repository = RestrictedProductsRepository()
        assert repository.find_match("an unrecognizable gadget xyz") is None


class TestHazardClassRepository:
    """Tests for HazardClassRepository."""

    def test_known_class_returns_info(self) -> None:
        repository = HazardClassRepository()
        info = repository.get_class_info("9")
        assert info is not None
        assert info["name"] == "Miscellaneous Dangerous Substances and Articles"

    def test_unknown_class_returns_none(self) -> None:
        repository = HazardClassRepository()
        assert repository.get_class_info("99") is None