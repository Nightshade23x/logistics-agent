"""Synthesizes four agent reports into one prioritized human answer."""

from ..shared_llm_client import LLMProvider

SYSTEM_PROMPT = (
    "You are a shipping operations advisor. You are given four structured "
    "reports from specialist systems: compliance, trade/duty, finance, and "
    "country risk. Write a single prioritized paragraph (4-6 sentences) for "
    "a logistics manager. Lead with anything that could block the shipment "
    "(compliance restrictions, sanctions). Then cover cost (duty, landed "
    "cost). Then note any risk factors. Be concrete and cite the actual "
    "numbers/statuses given. Do not invent data not present in the reports."
)


class SynthesisService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def synthesize(
        self, compliance_report: dict, trader_report: dict, finance_report: dict, risk_report: dict
    ) -> str:
        user_prompt = (
            f"Compliance report: {compliance_report}\n\n"
            f"Trade/duty report: {trader_report}\n\n"
            f"Finance report: {finance_report}\n\n"
            f"Risk report: {risk_report}"
        )
        return self._llm.generate(SYSTEM_PROMPT, user_prompt)