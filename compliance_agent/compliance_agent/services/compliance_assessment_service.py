"""Wraps ComplianceService into the standard agent contract envelope."""

from ..schemas.compliance import ComplianceCheckRequest
from ..schemas.agent_response import AgentResponse, HandoffRequest
from .compliance_service import ComplianceService


class ComplianceAssessmentService:
    def __init__(self, compliance_service: ComplianceService) -> None:
        self._compliance_service = compliance_service

    def assess(self, product_description: str, destination_country: str | None = None) -> AgentResponse:
        request = ComplianceCheckRequest(
            product_description=product_description, destination_country=destination_country
        )
        result = self._compliance_service.check(request)

        missing: list[str] = []
        if not result.matched:
            missing.append(
                f"Product '{product_description}' not found in reference dataset; "
                f"manual verification required."
            )
        if destination_country and result.destination_notes and not result.destination_restricted:
            missing.append(result.destination_notes)

        status = "partial" if missing else "ok"

        return AgentResponse(
            status=status,
            summary=(
                f"Compliance status for '{product_description}': {result.status}."
                + (f" Destination check for {destination_country}: "
                   f"{'restricted' if result.destination_restricted else 'no restriction on file'}."
                   if destination_country else "")
            ),
            plan=["Checked product against restricted-products dataset", "Checked destination-country restrictions"],
            report=result.model_dump(),
            input_resolution={
                "product_description": product_description,
                "destination_country": destination_country,
            },
            missing_information=missing,
            handoff_payload={
                "status": result.status,
                "hazard_class": result.hazard_class,
                "destination_restricted": result.destination_restricted,
                "required_permits": result.required_permits,
                "required_licenses": result.required_licenses,
                "required_certificates": result.required_certificates,
            },
            handoff_requests=[
                HandoffRequest(
                    target_agent="risk_agent",
                    reason="Destination sanctions status needed to cross-check compliance restrictions.",
                    fields_needed=["sanctions_status"],
                )
            ],
        )