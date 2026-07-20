"""Wraps the export-planning orchestrator into the standard agent contract."""

from ..schemas.export_plan import ExportPlanRequest
from ..schemas.agent_response import AgentResponse, HandoffRequest
from .orchestrator_service import OrchestratorService


class TradeAssessmentService:
    """Produces a standard AgentResponse envelope around an export plan."""

    def __init__(self, orchestrator_service: OrchestratorService) -> None:
        self._orchestrator_service = orchestrator_service

    def assess(self, request: ExportPlanRequest) -> AgentResponse:
        plan = self._orchestrator_service.plan(request)

        missing: list[str] = []
        if not plan.hs_code_result.matched:
            missing.append(
                f"Product '{request.product_description}' could not be classified "
                f"into an HS code; the default duty rate was used instead."
            )
        if not plan.fta_result.fta_exists:
            missing.append(
                f"No known Free Trade Agreement between {request.country_from} "
                f"and {request.country_to} on file."
            )

        status = "ok" if plan.hs_code_result.matched else "partial"

        return AgentResponse(
            status=status,
            summary=plan.summary,
            plan=[
                "Classified product into HS code",
                "Estimated duty rate",
                "Checked for applicable FTA",
                "Suggested export strategy",
            ],
            report={
                "hs_code": plan.hs_code_result.model_dump(),
                "duty": plan.duty_result.model_dump(),
                "fta": plan.fta_result.model_dump(),
                "export_strategy": plan.export_strategy_result.model_dump(),
            },
            input_resolution={
                "product_description": request.product_description,
                "country_from": request.country_from,
                "country_to": request.country_to,
                "target_market": request.target_market,
            },
            missing_information=missing,
            handoff_payload={
                "hs_code": plan.hs_code_result.hs_code,
                "duty_rate_percent": plan.duty_result.duty_rate_percent,
                "fta_exists": plan.fta_result.fta_exists,
                "agreement_name": plan.fta_result.agreement_name,
            },
            handoff_requests=[
                HandoffRequest(
                    target_agent="finance_agent",
                    reason="Duty rate and HS code needed to compute accurate landed cost.",
                    fields_needed=["duty_rate_percent", "hs_code"],
                ),
                HandoffRequest(
                    target_agent="risk_agent",
                    reason="Destination country risk/sanctions status needed before finalizing export strategy.",
                    fields_needed=["destination_country"],
                ),
            ],
        )