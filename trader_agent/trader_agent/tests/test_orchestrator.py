"""Tests for OrchestratorService and the plan_export tool.

Includes an isolated unit test using fake services, plus integration
tests that call plan_export directly against the real container.
"""

from ..services.orchestrator_service import OrchestratorService
from ..schemas.export_plan import ExportPlanRequest
from ..schemas.hs_code import HsCodeResponse
from ..schemas.duty import DutyResponse
from ..schemas.fta import FtaResponse
from ..schemas.export_strategy import ExportStrategyResponse

from .. import server


class FakeHsCodeService:
    """Fake HsCodeService returning a fixed matched result."""

    def classify(self, request) -> HsCodeResponse:
        return HsCodeResponse(
            product_description=request.product_description,
            hs_code="1234.56",
            matched_keyword="fake",
            matched=True,
            message="fake hs code message",
        )


class FakeDutyService:
    """Fake DutyService that records the hs_code it was called with."""

    def __init__(self) -> None:
        self.last_hs_code_used: str | None = None

    def calculate(self, request) -> DutyResponse:
        self.last_hs_code_used = request.hs_code
        return DutyResponse(
            country_from=request.country_from,
            country_to=request.country_to,
            hs_code=request.hs_code,
            duty_rate_percent=1.0,
            rate_source="fake_source",
            message="fake duty message",
        )


class FakeFtaService:
    """Fake FtaService returning a fixed agreement-found result."""

    def check(self, request) -> FtaResponse:
        return FtaResponse(
            country_from=request.country_from,
            country_to=request.country_to,
            fta_exists=True,
            agreement_name="Fake FTA",
            message="fake fta message",
        )


class FakeExportStrategyService:
    """Fake ExportStrategyService returning a fixed suggestion."""

    def suggest(self, request) -> ExportStrategyResponse:
        return ExportStrategyResponse(
            product_description=request.product_description,
            target_market=request.target_market,
            market_note="fake market note",
            strategy="fake strategy text",
        )


class TestOrchestratorServiceIsolated:
    """Unit tests for OrchestratorService using fake dependencies."""

    def test_plan_combines_all_four_results(self) -> None:
        fake_duty_service = FakeDutyService()
        orchestrator = OrchestratorService(
            hs_code_service=FakeHsCodeService(),
            duty_service=fake_duty_service,
            fta_service=FakeFtaService(),
            export_strategy_service=FakeExportStrategyService(),
        )

        response = orchestrator.plan(
            ExportPlanRequest(
                product_description="widget",
                country_from="Testland",
                country_to="Otherland",
                target_market="otherland",
            )
        )

        assert response.hs_code_result.hs_code == "1234.56"
        assert response.duty_result.duty_rate_percent == 1.0
        assert response.fta_result.agreement_name == "Fake FTA"
        assert response.export_strategy_result.market_note == "fake market note"
        assert "widget" in response.summary

    def test_matched_hs_code_is_passed_through_to_duty_service(self) -> None:
        fake_duty_service = FakeDutyService()
        orchestrator = OrchestratorService(
            hs_code_service=FakeHsCodeService(),
            duty_service=fake_duty_service,
            fta_service=FakeFtaService(),
            export_strategy_service=FakeExportStrategyService(),
        )

        orchestrator.plan(
            ExportPlanRequest(
                product_description="widget",
                country_from="Testland",
                country_to="Otherland",
                target_market="otherland",
            )
        )

        assert fake_duty_service.last_hs_code_used == "1234.56"


class UnmatchedFakeHsCodeService:
    """Fake HsCodeService that always fails to classify the product."""

    def classify(self, request) -> HsCodeResponse:
        return HsCodeResponse(
            product_description=request.product_description,
            hs_code=None,
            matched_keyword=None,
            matched=False,
            message="no match",
        )


class TestOrchestratorServiceUnmatchedHsCode:
    """Unit tests for the fallback path when HS classification finds no match."""

    def test_placeholder_hs_code_is_used_for_duty_calculation(self) -> None:
        fake_duty_service = FakeDutyService()
        orchestrator = OrchestratorService(
            hs_code_service=UnmatchedFakeHsCodeService(),
            duty_service=fake_duty_service,
            fta_service=FakeFtaService(),
            export_strategy_service=FakeExportStrategyService(),
        )

        orchestrator.plan(
            ExportPlanRequest(
                product_description="mystery item",
                country_from="Testland",
                country_to="Otherland",
                target_market="otherland",
            )
        )

        assert fake_duty_service.last_hs_code_used == "UNCLASSIFIED"


class TestPlanExportToolIntegration:
    """Integration tests for the plan_export tool against the real container."""

    def test_matched_product_returns_full_plan(self) -> None:
        response = server.plan_export("a nice laptop", "India", "Japan", "japan")
        assert response.hs_code_result.matched is True
        assert response.hs_code_result.hs_code == "8471.30"
        assert response.duty_result.hs_code == "8471.30"
        assert response.fta_result.fta_exists is True
        assert response.fta_result.agreement_name == "India-Japan CEPA"
        assert "laptop" in response.summary

    def test_unmatched_product_falls_back_gracefully(self) -> None:
        response = server.plan_export("a mystery gadget", "USA", "Canada", "usa")
        assert response.hs_code_result.matched is False
        assert response.duty_result.rate_source == "default_flat_rate"
        assert response.fta_result.fta_exists is True
        assert response.fta_result.agreement_name == "USMCA"