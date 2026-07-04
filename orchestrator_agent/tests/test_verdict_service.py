"""Tests for VerdictService -- pure rule-based logic, no LLM or network calls."""

import pytest

from orchestrator_agent.services.verdict_service import VerdictService


@pytest.fixture
def service() -> VerdictService:
    return VerdictService()


def make_compliance_report(status="ok", destination_restricted=False, product="widget"):
    return {
        "agent_name": "compliance_agent",
        "report": {
            "product_description": product,
            "reason": "test reason",
            "destination_notes": "test destination note",
        },
        "handoff_payload": {
            "status": status,
            "destination_restricted": destination_restricted,
            "required_certificates": [],
            "required_permits": [],
        },
    }


def make_risk_report(risk_tier="low", sanctions_status="no_sanctions", cpi_score=80):
    return {
        "report": {"sanctions": {"sanctions_status": sanctions_status}},
        "handoff_payload": {"risk_tier": risk_tier, "cpi_score": cpi_score},
    }


def make_trader_report(missing_information=None):
    return {"missing_information": missing_information or []}


class TestVerdictService:
    def test_clean_shipment_returns_clear_status(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="allowed"),
            trader_report=make_trader_report(),
            finance_report={},
            risk_report=make_risk_report(),
            agent_errors={},
        )
        assert verdict.status == "clear"
        assert verdict.blockers == []

    def test_prohibited_product_is_a_blocker(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="prohibited"),
            trader_report=make_trader_report(),
            finance_report={},
            risk_report=make_risk_report(),
            agent_errors={},
        )
        assert verdict.status == "blocked"
        assert any("prohibited" in b for b in verdict.blockers)

    def test_restricted_destination_is_a_blocker(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="restricted", destination_restricted=True),
            trader_report=make_trader_report(),
            finance_report={},
            risk_report=make_risk_report(),
            agent_errors={},
        )
        assert verdict.status == "blocked"
        assert any("destination note" in b.lower() for b in verdict.blockers)

    def test_unknown_compliance_status_is_a_warning_not_blocker(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="unknown"),
            trader_report=make_trader_report(),
            finance_report={},
            risk_report=make_risk_report(),
            agent_errors={},
        )
        assert verdict.status == "review_required"
        assert verdict.blockers == []
        assert any("not in the reference dataset" in w for w in verdict.warnings)

    def test_sanctioned_destination_is_a_blocker(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="allowed"),
            trader_report=make_trader_report(),
            finance_report={},
            risk_report=make_risk_report(sanctions_status="targeted_sanctions"),
            agent_errors={},
        )
        assert verdict.status == "blocked"
        assert any("sanctions" in b.lower() for b in verdict.blockers)

    def test_high_risk_tier_is_a_warning(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="allowed"),
            trader_report=make_trader_report(),
            finance_report={},
            risk_report=make_risk_report(risk_tier="high", cpi_score=35),
            agent_errors={},
        )
        assert verdict.status == "review_required"
        assert any("high" in w.lower() for w in verdict.warnings)

    def test_trader_missing_information_becomes_warnings(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="allowed"),
            trader_report=make_trader_report(missing_information=["No HS code match found."]),
            finance_report={},
            risk_report=make_risk_report(),
            agent_errors={},
        )
        assert verdict.status == "review_required"
        assert any("HS code" in w for w in verdict.warnings)

    def test_agent_errors_become_warnings(self, service):
        verdict = service.derive(
            compliance_report={},
            trader_report=make_trader_report(),
            finance_report={},
            risk_report={},
            agent_errors={"finance_agent": "Connection refused"},
        )
        assert verdict.status == "review_required"
        assert any("finance_agent" in w for w in verdict.warnings)

    def test_blockers_take_priority_over_warnings_in_headline(self, service):
        verdict = service.derive(
            compliance_report=make_compliance_report(status="prohibited"),
            trader_report=make_trader_report(missing_information=["No HS code match."]),
            finance_report={},
            risk_report=make_risk_report(risk_tier="high"),
            agent_errors={},
        )
        assert verdict.status == "blocked"
        assert "prohibited" in verdict.headline