"""Unit tests for the service layer.

Each service is tested in isolation using a lightweight fake repository,
so these tests verify service logic (normalization, response shaping)
without depending on the actual JSON reference data.
"""

from ..services.incoterms_service import IncotermsService
from ..services.hs_code_service import HsCodeService
from ..services.duty_service import DutyService
from ..services.fta_service import FtaService
from ..services.export_strategy_service import ExportStrategyService

from ..schemas.incoterms import IncotermRequest
from ..schemas.hs_code import HsCodeRequest
from ..schemas.duty import DutyRequest
from ..schemas.fta import FtaRequest
from ..schemas.export_strategy import ExportStrategyRequest


class FakeIncotermsRepository:
    """Minimal fake repository for testing IncotermsService in isolation."""

    def get_definition(self, term: str) -> str | None:
        return "Fake FOB definition" if term == "FOB" else None


class TestIncotermsService:
    """Tests for IncotermsService."""

    def test_known_term_is_marked_known(self) -> None:
        service = IncotermsService(FakeIncotermsRepository())
        response = service.explain(IncotermRequest(term="fob"))
        assert response.known is True
        assert response.term == "FOB"
        assert response.explanation == "Fake FOB definition"

    def test_unknown_term_is_marked_unknown(self) -> None:
        service = IncotermsService(FakeIncotermsRepository())
        response = service.explain(IncotermRequest(term="ZZZ"))
        assert response.known is False


class FakeHsCodeRepository:
    """Minimal fake repository for testing HsCodeService in isolation."""

    def find_match(self, normalized_description: str) -> tuple[str, str] | None:
        if "laptop" in normalized_description:
            return "laptop", "8471.30"
        return None


class TestHsCodeService:
    """Tests for HsCodeService."""

    def test_matched_description_returns_hs_code(self) -> None:
        service = HsCodeService(FakeHsCodeRepository())
        response = service.classify(HsCodeRequest(product_description="a laptop"))
        assert response.matched is True
        assert response.hs_code == "8471.30"
        assert response.matched_keyword == "laptop"

    def test_unmatched_description_returns_no_match(self) -> None:
        service = HsCodeService(FakeHsCodeRepository())
        response = service.classify(HsCodeRequest(product_description="a mystery item"))
        assert response.matched is False
        assert response.hs_code is None


class FakeDutyRepository:
    """Minimal fake repository for testing DutyService in isolation."""

    def get_default_rate(self) -> float:
        return 5.0

    def get_override_rate(self, hs_code: str) -> float | None:
        return 0.0 if hs_code == "8471.30" else None


class TestDutyService:
    """Tests for DutyService."""

    def test_override_rate_is_used_when_available(self) -> None:
        service = DutyService(FakeDutyRepository())
        response = service.calculate(
            DutyRequest(country_from="India", country_to="USA", hs_code="8471.30")
        )
        assert response.duty_rate_percent == 0.0
        assert response.rate_source == "hs_code_override"

    def test_default_rate_is_used_when_no_override(self) -> None:
        service = DutyService(FakeDutyRepository())
        response = service.calculate(
            DutyRequest(country_from="India", country_to="USA", hs_code="0000.00")
        )
        assert response.duty_rate_percent == 5.0
        assert response.rate_source == "default_flat_rate"


class FakeFtaRepository:
    """Minimal fake repository for testing FtaService in isolation."""

    def find_agreement(self, country_a: str, country_b: str) -> str | None:
        if {country_a, country_b} == {"india", "japan"}:
            return "India-Japan CEPA"
        return None


class TestFtaService:
    """Tests for FtaService."""

    def test_known_pair_reports_agreement_found(self) -> None:
        service = FtaService(FakeFtaRepository())
        response = service.check(FtaRequest(country_from="India", country_to="Japan"))
        assert response.fta_exists is True
        assert response.agreement_name == "India-Japan CEPA"

    def test_unknown_pair_reports_no_agreement(self) -> None:
        service = FtaService(FakeFtaRepository())
        response = service.check(FtaRequest(country_from="Atlantis", country_to="Narnia"))
        assert response.fta_exists is False
        assert response.agreement_name is None


class FakeExportStrategyRepository:
    """Minimal fake repository for testing ExportStrategyService in isolation."""

    def get_market_note(self, normalized_market: str) -> str:
        return "Fake USA note" if normalized_market == "usa" else "Fake default note"


class TestExportStrategyService:
    """Tests for ExportStrategyService."""

    def test_strategy_includes_market_note(self) -> None:
        service = ExportStrategyService(FakeExportStrategyRepository())
        response = service.suggest(
            ExportStrategyRequest(product_description="shoes", target_market="usa")
        )
        assert response.market_note == "Fake USA note"
        assert "Fake USA note" in response.strategy

    def test_strategy_falls_back_to_default_note(self) -> None:
        service = ExportStrategyService(FakeExportStrategyRepository())
        response = service.suggest(
            ExportStrategyRequest(product_description="shoes", target_market="atlantis")
        )
        assert response.market_note == "Fake default note"