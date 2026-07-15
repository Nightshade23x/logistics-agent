"""Unit tests for the repository layer.

These tests confirm that each repository correctly loads its JSON data
file and exposes the expected lookup behavior, independent of any
service logic.
"""

from ..repositories.incoterms_repository import IncotermsRepository
from ..repositories.hs_code_repository import HsCodeRepository
from ..repositories.duty_repository import DutyRepository
from ..repositories.fta_repository import FtaRepository
from ..repositories.export_strategy_repository import ExportStrategyRepository


class TestIncotermsRepository:
    """Tests for IncotermsRepository."""

    def test_known_term_returns_definition(self) -> None:
        repository = IncotermsRepository()
        assert repository.get_definition("FOB") is not None
        assert "Free On Board" in repository.get_definition("FOB")

    def test_unknown_term_returns_none(self) -> None:
        repository = IncotermsRepository()
        assert repository.get_definition("ZZZ") is None


class TestHsCodeRepository:
    """Tests for HsCodeRepository."""

    def test_known_keyword_returns_match(self) -> None:
        repository = HsCodeRepository()
        result = repository.find_match("a nice laptop for work")
        assert result is not None
        keyword, hs_code = result
        assert keyword == "laptop"
        assert hs_code == "8471.30"

    def test_unknown_description_returns_none(self) -> None:
        repository = HsCodeRepository()
        assert repository.find_match("an unrecognizable gadget xyz") is None


class TestDutyRepository:
    """Tests for DutyRepository."""

    def test_default_rate_is_positive(self) -> None:
        repository = DutyRepository()
        assert repository.get_default_rate() >= 0

    def test_known_hs_code_override(self) -> None:
        repository = DutyRepository()
        assert repository.get_override_rate("8471.30") == 0.0

    def test_unknown_hs_code_returns_none(self) -> None:
        repository = DutyRepository()
        assert repository.get_override_rate("0000.00") is None


class TestFtaRepository:
    """Tests for FtaRepository."""

    def test_known_pair_returns_agreement(self) -> None:
        repository = FtaRepository()
        assert repository.find_agreement("india", "japan") == "India-Japan CEPA"

    def test_order_independent_lookup(self) -> None:
        repository = FtaRepository()
        assert repository.find_agreement("japan", "india") == "India-Japan CEPA"

    def test_unknown_pair_returns_none(self) -> None:
        repository = FtaRepository()
        assert repository.find_agreement("atlantis", "narnia") is None


class TestExportStrategyRepository:
    """Tests for ExportStrategyRepository."""

    def test_known_market_returns_specific_note(self) -> None:
        repository = ExportStrategyRepository()
        note = repository.get_market_note("usa")
        assert "FDA" in note

    def test_unknown_market_returns_default_note(self) -> None:
        repository = ExportStrategyRepository()
        note = repository.get_market_note("atlantis")
        assert note == repository._default_note