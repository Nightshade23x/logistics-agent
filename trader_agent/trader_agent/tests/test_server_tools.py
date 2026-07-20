"""Integration tests for the MCP server's tool functions.

These tests call the tool functions defined in server.py directly
(they remain plain callables even after @mcp.tool() registration),
exercising the full path: request validation -> real container ->
real repository-backed service -> structured response.
"""

import pytest
from pydantic import ValidationError

from .. import server


class TestExplainIncotermTool:
    """Integration tests for the explain_incoterm tool."""

    def test_known_term_returns_explanation(self) -> None:
        response = server.explain_incoterm("FOB")
        assert response.known is True
        assert "Free On Board" in response.explanation

    def test_invalid_input_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            server.explain_incoterm("")


class TestClassifyHsCodeTool:
    """Integration tests for the classify_hs_code tool."""

    def test_known_product_returns_hs_code(self) -> None:
        response = server.classify_hs_code("a nice laptop")
        assert response.matched is True
        assert response.hs_code == "8471.30"

    def test_invalid_input_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            server.classify_hs_code("")


class TestCalculateDutyTool:
    """Integration tests for the calculate_duty tool."""

    def test_known_hs_code_returns_override_rate(self) -> None:
        response = server.calculate_duty("India", "USA", "8471.30")
        assert response.duty_rate_percent == 0.0
        assert response.rate_source == "hs_code_override"

    def test_unknown_hs_code_returns_default_rate(self) -> None:
        response = server.calculate_duty("India", "USA", "0000.00")
        assert response.rate_source == "default_flat_rate"


class TestCheckFtaTool:
    """Integration tests for the check_fta tool."""

    def test_known_pair_reports_agreement(self) -> None:
        response = server.check_fta("India", "Japan")
        assert response.fta_exists is True
        assert response.agreement_name == "India-Japan CEPA"

    def test_unknown_pair_reports_no_agreement(self) -> None:
        response = server.check_fta("Atlantis", "Narnia")
        assert response.fta_exists is False


class TestSuggestExportStrategyTool:
    """Integration tests for the suggest_export_strategy tool."""

    def test_known_market_includes_market_note(self) -> None:
        response = server.suggest_export_strategy("leather shoes", "usa")
        assert "FDA" in response.market_note
        assert "leather shoes" in response.strategy


class TestServerSetup:
    """Sanity checks on the overall server and container wiring."""

    def test_mcp_instance_has_expected_name(self) -> None:
        assert server.mcp.name == "Trader Agent"

    def test_container_has_all_services(self) -> None:
        assert server.container.incoterms_service is not None
        assert server.container.hs_code_service is not None
        assert server.container.duty_service is not None
        assert server.container.fta_service is not None
        assert server.container.export_strategy_service is not None