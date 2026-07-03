"""Composes country risk and sanctions checks into the standard agent contract."""

from ..schemas.envelope import AgentResponse, HandoffRequest
from ..schemas.country_risk import CountryRiskRequest
from ..schemas.sanctions import CountrySanctionsRequest
from .country_risk_service import CountryRiskService
from .sanctions_service import SanctionsService


class RiskAssessmentService:
    """Top-level orchestrator that returns the standard AgentResponse contract."""

    def __init__(
        self,
        country_risk_service: CountryRiskService,
        sanctions_service: SanctionsService,
    ) -> None:
        self._country_risk_service = country_risk_service
        self._sanctions_service = sanctions_service

    def assess(self, country: str) -> AgentResponse:
        """Run all available risk checks for a country and build the envelope.

        Args:
            country: Destination or origin country name to assess.

        Returns:
            A fully populated AgentResponse.
        """
        risk = self._country_risk_service.get_risk(CountryRiskRequest(country=country))
        sanctions = self._sanctions_service.get_country(CountrySanctionsRequest(country=country))

        missing: list[str] = []
        if not risk.found:
            missing.append(f"No CPI corruption data found for '{country}'.")
        if not sanctions.found:
            missing.append(f"No sanctions data found for '{country}'.")

        # These proxies aren't implemented yet — flag explicitly rather than
        # silently omitting them, so the orchestrator / client knows they're absent.
        missing.extend([
            "Weather risk not yet implemented.",
            "Port congestion risk not yet implemented.",
            "Natural disaster risk not yet implemented.",
            "Alternate route suggestions not yet implemented.",
        ])

        status = "ok" if (risk.found and sanctions.found) else "partial"

        summary_parts = []
        if risk.found:
            summary_parts.append(f"{country} has a CPI corruption risk tier of '{risk.risk_tier}'.")
        else:
            summary_parts.append(f"No corruption risk data available for {country}.")
        if sanctions.found:
            summary_parts.append(f"Sanctions status: {sanctions.sanctions_status}.")
        else:
            summary_parts.append("No sanctions data available.")

        return AgentResponse(
            status=status,
            summary=" ".join(summary_parts),
            plan=[
                "Looked up CPI corruption score",
                "Looked up sanctions status and programs",
            ],
            report={
                "country_risk": risk.model_dump(),
                "sanctions": sanctions.model_dump(),
            },
            input_resolution={"requested_country": country},
            missing_information=missing,
            handoff_payload={
                "risk_tier": risk.risk_tier,
                "cpi_score": risk.cpi_score,
                "sanctions_status": sanctions.sanctions_status,
                "sanctions_programs": sanctions.programs,
            },
            handoff_requests=[
                HandoffRequest(
                    target_agent="logistics_agent",
                    reason="Route data needed to assess port congestion and alternate routing risk.",
                    fields_needed=["planned_route", "destination_port"],
                )
            ],
        )