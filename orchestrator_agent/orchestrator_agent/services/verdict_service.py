"""Derives a structured verdict (clear/review_required/blocked) from agent reports.

This is rule-based, not LLM-based -- the verdict itself should be
deterministic and auditable, even though the synthesis paragraph uses LLM
reasoning. Blockers/warnings are collected from what each agent already
flagged, not re-interpreted by a model.
"""

from ..schemas.orchestrated_response import Verdict


class VerdictService:
    def derive(
        self,
        compliance_report: dict,
        trader_report: dict,
        finance_report: dict,
        risk_report: dict,
        agent_errors: dict[str, str],
    ) -> Verdict:
        blockers: list[str] = []
        warnings: list[str] = []
        next_steps: list[str] = []

        if agent_errors:
            for agent_name, error in agent_errors.items():
                warnings.append(f"{agent_name} did not respond ({error}); its data is unavailable.")

        if compliance_report:
            if compliance_report.get("status") == "prohibited":
                blockers.append(
                    f"Compliance: '{compliance_report.get('product_description')}' is prohibited "
                    f"for trade -- {compliance_report.get('reason', '')}"
                )
            elif compliance_report.get("status") == "restricted":
                warnings.append(
                    f"Compliance: '{compliance_report.get('product_description')}' is restricted "
                    f"-- {compliance_report.get('reason', '')}"
                )
                next_steps.extend(compliance_report.get("required_certificates", []))
                next_steps.extend(compliance_report.get("required_permits", []))
            elif compliance_report.get("status") == "unknown":
                warnings.append(
                    f"Compliance: '{compliance_report.get('product_description')}' is not in the "
                    f"reference dataset -- manual verification required before shipping."
                )
            if compliance_report.get("destination_restricted"):
                blockers.append(f"Compliance: {compliance_report.get('destination_notes', '')}")

        if risk_report.get("report", {}).get("sanctions", {}).get("sanctions_status") not in (
            None, "unknown", "no_sanctions",
        ):
            blockers.append(
                f"Risk: sanctions status is "
                f"'{risk_report['report']['sanctions']['sanctions_status']}' for the destination."
            )
        if risk_report.get("handoff_payload", {}).get("risk_tier") in ("high", "severe"):
            warnings.append(
                f"Risk: destination has a '{risk_report['handoff_payload']['risk_tier']}' "
                f"corruption risk tier (CPI {risk_report['handoff_payload'].get('cpi_score')})."
            )

        if trader_report.get("missing_information"):
            warnings.extend(f"Trade: {item}" for item in trader_report["missing_information"])

        if blockers:
            status = "blocked"
            headline = blockers[0]
        elif warnings:
            status = "review_required"
            headline = "Shipment can proceed pending review of flagged items."
        else:
            status = "clear"
            headline = "No blockers or warnings identified for this shipment."

        return Verdict(
            status=status,
            headline=headline,
            blockers=blockers,
            warnings=warnings,
            next_steps=next_steps,
        )