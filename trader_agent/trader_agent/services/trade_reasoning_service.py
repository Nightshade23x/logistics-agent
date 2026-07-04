"""Adds LLM judgment on top of the deterministic export plan assessment."""

from .trade_assessment_service import TradeAssessmentService
from ..shared_llm_client import LLMProvider

SYSTEM_PROMPT = (
    "You are a trade strategy advisor. Given a structured export plan "
    "(HS code classification, duty rate, FTA status, suggested export "
    "strategy), write a 2-3 sentence practical recommendation for an "
    "exporter: does the suggested strategy actually make sense given the "
    "duty rate and FTA status, and what should they prioritize next? "
    "Be concrete and specific to the numbers given. Do not invent data "
    "not present in the input."
)


class TradeReasoningService:
    """Wraps TradeAssessmentService with an LLM-generated judgment."""

    def __init__(
        self, trade_assessment_service: TradeAssessmentService, llm: LLMProvider
    ) -> None:
        self._trade_assessment_service = trade_assessment_service
        self._llm = llm

    def assess_with_reasoning(self, request):
        response = self._trade_assessment_service.assess(request)

        user_prompt = (
            f"Product: {request.product_description}\n"
            f"Route: {request.country_from} -> {request.country_to}\n"
            f"Target market: {request.target_market}\n"
            f"Structured report: {response.report}\n"
            f"Missing information: {response.missing_information}"
        )

        judgment = self._llm.generate(SYSTEM_PROMPT, user_prompt)
        response.report["llm_judgment"] = judgment
        return response