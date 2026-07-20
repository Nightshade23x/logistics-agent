"""Service that orchestrates the other services into a single export-planning workflow."""

from ..schemas.export_plan import ExportPlanRequest, ExportPlanResponse
from ..schemas.hs_code import HsCodeRequest
from ..schemas.duty import DutyRequest
from ..schemas.fta import FtaRequest
from ..schemas.export_strategy import ExportStrategyRequest

from .hs_code_service import HsCodeService
from .duty_service import DutyService
from .fta_service import FtaService
from .export_strategy_service import ExportStrategyService


class OrchestratorService:
    """Coordinates HS code classification, duty, FTA, and export strategy.

    This service does not contain its own business rules; it composes
    the four existing services in sequence and combines their results.
    Each dependency is injected so the orchestrator can be unit tested
    with fakes, exactly like the individual services.
    """

    _UNCLASSIFIED_HS_CODE_PLACEHOLDER: str = "UNCLASSIFIED"

    def __init__(
        self,
        hs_code_service: HsCodeService,
        duty_service: DutyService,
        fta_service: FtaService,
        export_strategy_service: ExportStrategyService,
    ) -> None:
        """Initialize the OrchestratorService with its four service dependencies.

        Args:
            hs_code_service: Used to classify the product into an HS code.
            duty_service: Used to estimate duty for the shipment.
            fta_service: Used to check for an applicable FTA.
            export_strategy_service: Used to suggest an export strategy.
        """
        self._hs_code_service = hs_code_service
        self._duty_service = duty_service
        self._fta_service = fta_service
        self._export_strategy_service = export_strategy_service

    def plan(self, request: ExportPlanRequest) -> ExportPlanResponse:
        """Run the full export-planning workflow for a product and market.

        Steps:
            1. Classify the product into an HS code.
            2. Estimate duty using the classified HS code (or a placeholder
               code if classification found no match, which falls back to
               the default duty rate).
            3. Check whether an FTA exists between the two countries.
            4. Suggest an export strategy for the target market.

        Args:
            request: The validated export plan request.

        Returns:
            An ExportPlanResponse containing all four step results plus
            a combined summary.
        """
        hs_code_result = self._hs_code_service.classify(
            HsCodeRequest(product_description=request.product_description)
        )

        duty_lookup_code = (
            hs_code_result.hs_code
            if hs_code_result.matched and hs_code_result.hs_code is not None
            else self._UNCLASSIFIED_HS_CODE_PLACEHOLDER
        )
        duty_result = self._duty_service.calculate(
            DutyRequest(
                country_from=request.country_from,
                country_to=request.country_to,
                hs_code=duty_lookup_code,
            )
        )

        fta_result = self._fta_service.check(
            FtaRequest(country_from=request.country_from, country_to=request.country_to)
        )

        export_strategy_result = self._export_strategy_service.suggest(
            ExportStrategyRequest(
                product_description=request.product_description,
                target_market=request.target_market,
            )
        )

        summary = self._build_summary(
            request, hs_code_result, duty_result, fta_result, export_strategy_result
        )

        return ExportPlanResponse(
            hs_code_result=hs_code_result,
            duty_result=duty_result,
            fta_result=fta_result,
            export_strategy_result=export_strategy_result,
            summary=summary,
        )

    def _build_summary(
        self,
        request: ExportPlanRequest,
        hs_code_result,
        duty_result,
        fta_result,
        export_strategy_result,
    ) -> str:
        """Build a concise human-readable summary of all four step results.

        Args:
            request: The original export plan request.
            hs_code_result: Result of HS code classification.
            duty_result: Result of duty calculation.
            fta_result: Result of the FTA check.
            export_strategy_result: Result of the export strategy suggestion.

        Returns:
            A single paragraph summarizing the full export plan.
        """
        if hs_code_result.matched:
            hs_code_summary = f"classified as HS code {hs_code_result.hs_code}"
        else:
            hs_code_summary = (
                "could not be automatically classified; the default duty rate was used"
            )

        fta_summary = (
            f"a Free Trade Agreement ({fta_result.agreement_name}) applies"
            if fta_result.fta_exists
            else "no known Free Trade Agreement applies"
        )

        return (
            f"Export plan for '{request.product_description}' from "
            f"{request.country_from} to {request.country_to}, targeting "
            f"{request.target_market}: the product was {hs_code_summary}, "
            f"with an estimated duty rate of {duty_result.duty_rate_percent}%. "
            f"Between {request.country_from} and {request.country_to}, "
            f"{fta_summary}. Recommended next step: "
            f"{export_strategy_result.market_note}"
        )