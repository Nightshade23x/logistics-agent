"""Tests for RiskAssessmentService (the standard agent-contract orchestrator)."""

import pytest

from risk_agent.container import build_container
from risk_agent.schemas.envelope import AgentResponse


@pytest.fixture(scope="module")
def container():
    return build_container()


class TestAssessTradeRisk:
    def test_known_country_with_sanctions_returns_ok_status(self, container):
        result = container.risk_assessment_service.assess("Russia")

        assert isinstance(result, AgentResponse)
        assert result.agent_name == "risk_agent"
        assert result.status == "ok"
        assert result.report["country_risk"]["found"] is True
        assert result.report["sanctions"]["found"] is True
        assert result.handoff_payload["risk_tier"] == "severe"
        assert result.handoff_payload["sanctions_status"] == "targeted_sanctions"

    def test_known_country_without_sanctions_data_returns_partial(self, container):
        result = container.risk_assessment_service.assess("Brazil")

        assert result.status == "partial"
        assert result.report["country_risk"]["found"] is True
        assert result.report["sanctions"]["found"] is False
        assert "No sanctions data found for 'Brazil'." in result.missing_information

    def test_unrecognized_country_returns_partial_with_nulls(self, container):
        result = container.risk_assessment_service.assess("Not A Real Country")

        assert result.status == "partial"
        assert result.report["country_risk"]["found"] is False
        assert result.report["sanctions"]["found"] is False
        assert result.handoff_payload["risk_tier"] is None
        assert result.handoff_payload["cpi_score"] is None

    def test_missing_information_always_lists_unimplemented_risk_types(self, container):
        result = container.risk_assessment_service.assess("Russia")

        expected_gaps = {
            "Weather risk not yet implemented.",
            "Port congestion risk not yet implemented.",
            "Natural disaster risk not yet implemented.",
            "Alternate route suggestions not yet implemented.",
        }
        assert expected_gaps.issubset(set(result.missing_information))

    def test_handoff_requests_targets_logistics_agent(self, container):
        result = container.risk_assessment_service.assess("Russia")

        assert len(result.handoff_requests) == 1
        assert result.handoff_requests[0].target_agent == "logistics_agent"
        assert "planned_route" in result.handoff_requests[0].fields_needed