from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_OUTPUTS = ROOT / "demo_outputs"
FINAL_BUNDLE = DEMO_OUTPUTS / "final_demo_bundle"


def run_command(command: list[str], allow_failure: bool = False) -> tuple[int, str]:
    env = os.environ.copy()
    env.pop("TRADE_ORCHESTRATOR_BASE_URL", None)
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    output = result.stdout

    if result.stderr.strip():
        output += "\n\nSTDERR:\n" + result.stderr

    if result.returncode != 0 and not allow_failure:
        print(output)
        raise SystemExit(result.returncode)

    return result.returncode, output


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def build_final_index(generated_files: list[str]) -> str:
    lines = [
        "# Final Demo Bundle",
        "",
        "## Purpose",
        "",
        "This folder contains the main evidence for the backend demo.",
        "",
        "It includes:",
        "",
        "- standalone backend demo outputs",
        "- frontend payload outputs",
        "- logistics scenario reports",
        "- document AI reports",
        "- partner stack checker output",
        "- project documentation",
        "- all-demo check results",
        "",
        "## Main Demo Command",
        "",
        "```powershell",
        "cd C:\\Users\\Samar\\Desktop\\logistics-agent",
        ".\\.venv\\Scripts\\Activate.ps1",
        "python scripts\\run_all_demo_checks.py",
        "```",
        "",
        "Expected result:",
        "",
        "```text",
        "ALL DEMO CHECKS PASSED",
        "```",
        "",
        "## Export Command",
        "",
        "```powershell",
        "python scripts\\export_final_demo_bundle.py",
        "```",
        "",
        "## What The Demo Shows",
        "",
        "1. User Agent routes shopping, logistics, and document workflows.",
        "2. Shopping Agent selects suppliers and procurement guidance.",
        "3. Logistics Agent produces container planning, risk, packaging, and loading advice.",
        "4. Logistics Visualizer returns frontend-ready container/cargo layout data.",
        "5. Document AI parses and validates invoice, packing list, BOL, and certificate documents.",
        "6. Partner Review Service can run safely offline or call the live orchestrator when configured.",
        "7. The backend returns structured frontend payloads, not just raw text.",
        "",
        "## Current Partner Status",
        "",
        "The backend partner adapter is integrated.",
        "",
        "Known external blocker:",
        "",
        "```text",
        "trader_agent requires OPENAI_API_KEY and partner-side setup",
        "```",
        "",
        "Standalone backend demo does not depend on this.",
        "",
        "## Generated Files",
        "",
    ]

    for file_name in generated_files:
        lines.append(f"- `{file_name}`")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    DEMO_OUTPUTS.mkdir(exist_ok=True)

    if FINAL_BUNDLE.exists():
        shutil.rmtree(FINAL_BUNDLE)

    FINAL_BUNDLE.mkdir(parents=True, exist_ok=True)

    generated_files: list[str] = []

    checks_code, checks_output = run_command(
        [sys.executable, "scripts/run_all_demo_checks.py"]
    )
    write_text(FINAL_BUNDLE / "checks" / "all_demo_checks.txt", checks_output)
    generated_files.append("checks/all_demo_checks.txt")

    export_code, export_output = run_command(
        [sys.executable, "scripts/export_demo_pack.py"]
    )
    write_text(FINAL_BUNDLE / "checks" / "export_demo_pack_output.txt", export_output)
    generated_files.append("checks/export_demo_pack_output.txt")

    for filename in [
        "backend_status.json",
        "frontend_payload_shopping.json",
        "frontend_payload_compact.json",
        "demo_report.md",
        "demo_index.md",
    ]:
        copy_if_exists(DEMO_OUTPUTS / filename, FINAL_BUNDLE / "shopping_demo" / filename)
        generated_files.append(f"shopping_demo/{filename}")

    static_frontend_code, static_frontend_output = run_command(
        [sys.executable, "scripts/export_static_frontend_demo.py"]
    )
    write_text(
        FINAL_BUNDLE / "checks" / "static_frontend_demo_output.txt",
        static_frontend_output,
    )
    generated_files.append("checks/static_frontend_demo_output.txt")

    copy_if_exists(
        DEMO_OUTPUTS / "frontend_demo.html",
        FINAL_BUNDLE / "frontend" / "frontend_demo.html",
    )
    generated_files.append("frontend/frontend_demo.html")

    logistics_scenarios_code, logistics_scenarios_output = run_command(
        [sys.executable, "scripts/run_logistics_scenarios.py"]
    )
    write_text(
        FINAL_BUNDLE / "logistics" / "logistics_scenario_pack.txt",
        logistics_scenarios_output,
    )
    generated_files.append("logistics/logistics_scenario_pack.txt")

    oversized_code, oversized_output = run_command(
        [
            sys.executable,
            "scripts/run_logistics_plan.py",
            "data/scenarios/oversized_multi_container.json",
        ]
    )
    write_text(
        FINAL_BUNDLE / "logistics" / "oversized_logistics_report.txt",
        oversized_output,
    )
    generated_files.append("logistics/oversized_logistics_report.txt")

    document_agent_code, document_agent_output = run_command(
        [sys.executable, "scripts/run_document_agent.py"]
    )
    write_text(
        FINAL_BUNDLE / "documents" / "document_agent_report.txt",
        document_agent_output,
    )
    generated_files.append("documents/document_agent_report.txt")

    document_pair_code, document_pair_output = run_command(
        [sys.executable, "scripts/run_document_pair_agent.py"]
    )
    write_text(
        FINAL_BUNDLE / "documents" / "document_pair_validation_report.txt",
        document_pair_output,
    )
    generated_files.append("documents/document_pair_validation_report.txt")

    document_set_code, document_set_output = run_command(
        [sys.executable, "scripts/run_document_set_agent.py"]
    )
    write_text(
        FINAL_BUNDLE / "documents" / "document_set_completeness_report.txt",
        document_set_output,
    )
    generated_files.append("documents/document_set_completeness_report.txt")

    live_partner_code, live_partner_output = run_command(
        [sys.executable, "scripts/check_live_partner_stack.py"],
        allow_failure=True,
    )
    write_text(
        FINAL_BUNDLE / "partner" / "live_partner_stack_check.txt",
        live_partner_output,
    )
    generated_files.append("partner/live_partner_stack_check.txt")

    docs_to_copy = [
        "docs/demo_runbook.md",
        "docs/frontend_payload_contract.md",
        "docs/backend_agent_status_report.md",
    ]

    for relative_path in docs_to_copy:
        source = ROOT / relative_path
        destination = FINAL_BUNDLE / "docs" / source.name
        copy_if_exists(source, destination)

        if source.exists():
            generated_files.append(f"docs/{source.name}")

    final_index = build_final_index(generated_files)
    write_text(FINAL_BUNDLE / "README.md", final_index)
    generated_files.insert(0, "README.md")

    print(f"Exported final demo bundle to: {FINAL_BUNDLE}")
    print("")
    print("Generated files:")

    for file_name in generated_files:
        print(f"- {file_name}")

    print("")
    print("Summary:")
    print("- all_demo_checks: passed")
    print("- shopping/frontend demo: exported")
    print("- logistics reports: exported")
    print("- document reports: exported")
    print("- live partner check: exported")
    print("- docs: copied")


if __name__ == "__main__":
    main()
