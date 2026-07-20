"""Synthesizes specialist agent reports into a final human-readable answer.

Gemini is used when available. If Gemini is unavailable or rate-limited, this
service falls back to a deterministic summary so /orchestrate still returns a
valid response instead of HTTP 500.
"""

from __future__ import annotations

import json
from typing import Any

from ..shared_llm_client import LLMProvider


SYSTEM_PROMPT = (
    "You are the synthesis layer of a trade orchestration system. "
    "Given reports from compliance, trade, finance, risk, and any agent errors, "
    "write a concise final answer. Highlight blockers first, then warnings, "
    "then costs and next steps. Do not invent facts."
)


class SynthesisService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def synthesize(
        self,
        compliance_report: dict[str, Any],
        trader_report: dict[str, Any],
        finance_report: dict[str, Any],
        risk_report: dict[str, Any],
        agent_errors: dict[str, Any],
    ) -> str:
        user_prompt = (
            f"Compliance report: {json.dumps(compliance_report, default=str)}\n"
            f"Trader report: {json.dumps(trader_report, default=str)}\n"
            f"Finance report: {json.dumps(finance_report, default=str)}\n"
            f"Risk report: {json.dumps(risk_report, default=str)}\n"
            f"Agent failures: {json.dumps(agent_errors or {}, default=str)}"
        )

        try:
            return self._llm.generate(SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            return self._fallback_synthesis(
                compliance_report=compliance_report,
                trader_report=trader_report,
                finance_report=finance_report,
                risk_report=risk_report,
                agent_errors=agent_errors,
                error=exc,
            )

    def _fallback_synthesis(
        self,
        compliance_report: dict[str, Any],
        trader_report: dict[str, Any],
        finance_report: dict[str, Any],
        risk_report: dict[str, Any],
        agent_errors: dict[str, Any],
        error: Exception,
    ) -> str:
        parts: list[str] = []

        finance_total = finance_report.get("total_cost") or finance_report.get("landed_cost")
        currency = finance_report.get("currency", "USD")
        if finance_total is not None:
            parts.append(f"Estimated landed cost is {finance_total} {currency}.")

        compliance_summary = compliance_report.get("summary")
        compliance_status = compliance_report.get("status")
        if compliance_summary:
            parts.append(f"Compliance: {compliance_summary}")
        elif compliance_status:
            parts.append(f"Compliance status: {compliance_status}.")

        trader_summary = trader_report.get("summary")
        if trader_summary:
            parts.append(f"Trade: {trader_summary}")

        risk_summary = risk_report.get("summary")
        if risk_summary:
            parts.append(f"Risk: {risk_summary}")

        if agent_errors:
            parts.append(f"Some agent calls failed or returned errors: {agent_errors}.")

        parts.append(
            "Gemini synthesis was unavailable, so this is a deterministic fallback summary. "
            f"Reason: {type(error).__name__}: {error}"
        )

        return " ".join(parts)
