"""Synthesizes four agent reports into one prioritized human answer."""

from ..shared_llm_client import LLMProvider

SYSTEM_PROMPT = (
    "You are a shipping operations advisor. You are given four structured "
    "reports from specialist systems: compliance, trade/duty, finance, and "
    "country risk. Write a single prioritized paragraph (4-6 sentences) for "
    "a logistics manager. Lead with anything that could block the shipment "
    "(compliance restrictions, sanctions). Then cover cost (duty, landed "
    "cost). Then note any risk factors. Be concrete and cite the actual "
    "numbers/statuses given. Do not invent data not present in the reports. "
    "If any agent failed to respond, its report will be empty -- clearly "
    "state that this information is currently unavailable rather than "
    "guessing or ignoring the gap."
)


class SynthesisService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def synthesize(
        self,
        compliance_report: dict,
        trader_report: dict,
        finance_report: dict,
        risk_report: dict,
        agent_errors: dict[str, str] | None = None,
    ) -> str:
        agent_errors = agent_errors or {}
        user_prompt = (
            f"Compliance report: {compliance_report or '[UNAVAILABLE]'}\n\n"
            f"Trade/duty report: {trader_report or '[UNAVAILABLE]'}\n\n"
            f"Finance report: {finance_report or '[UNAVAILABLE]'}\n\n"
            f"Risk report: {risk_report or '[UNAVAILABLE]'}\n\n"
            f"Agent failures: {agent_errors or 'None'}"
        )
        return self._llm.generate(SYSTEM_PROMPT, user_prompt)