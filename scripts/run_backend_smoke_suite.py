from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str], env_updates: dict[str, str | None] | None = None) -> bool:
    print("\n" + "=" * 90)
    print(f"RUNNING: {name}")
    print("=" * 90)

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'trader_agent'}{os.pathsep}{ROOT}"

    if env_updates:
        for key, value in env_updates.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value

    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode == 0:
        print(f"\nPASSED: {name}")
        return True

    print(f"\nFAILED: {name}")
    print(f"Exit code: {result.returncode}")
    return False


def main() -> int:
    failures: list[str] = []

    checks: list[tuple[str, list[str], dict[str, str | None]]] = [
        (
            "Compile core backend files",
            [
                sys.executable,
                "-m",
                "py_compile",
                "app/user_agent.py",
                "app/trader_adapter.py",
                "app/partner_review_service.py",
                "app/partner_request_builder.py",
                "app/partner_review_payload_validator.py",
            ],
            {},
        ),
        (
            "User Agent regression tests with Trader disabled",
            [sys.executable, "scripts/test_user_agent.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": None,
            },
        ),
        (
            "Direct text -> Trader routing",
            [sys.executable, "scripts/test_direct_trader_routing.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": "1",
            },
        ),
        (
            "Shopping/Document -> Logistics -> Trader integration",
            [sys.executable, "scripts/test_full_trader_integration.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": "1",
            },
        ),
        (
            "Document AI -> Logistics -> Trader integration",
            [sys.executable, "scripts/test_document_trader_integration.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": "1",
            },
        ),
        (
            "Partner review observability fields",
            [sys.executable, "scripts/test_partner_review_observability.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": None,
                "TRADE_ORCHESTRATOR_BASE_URL": None,
            },
        ),
        (
            "Partner payload enrichment fields",
            [sys.executable, "scripts/test_partner_payload_enrichment.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": "1",
                "TRADE_ORCHESTRATOR_BASE_URL": None,
            },
        ),
        (
            "Partner payload contract across entry paths",
            [sys.executable, "scripts/test_partner_payload_contract.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": "1",
                "TRADE_ORCHESTRATOR_BASE_URL": None,
            },
        ),
    ]

    for name, command, env_updates in checks:
        if not run_step(name, command, env_updates):
            failures.append(name)

    live_url = os.environ.get("TRADE_ORCHESTRATOR_BASE_URL", "").strip()

    if live_url:
        live_script = ROOT / "scripts" / "check_live_partner_stack.py"
        if live_script.exists():
            ok = run_step(
                "Optional live partner stack check",
                [sys.executable, "scripts/check_live_partner_stack.py"],
                {
                    "USE_TRAINED_ROUTER": "1",
                    "ENABLE_TRADER_AGENT": "1",
                    "TRADE_ORCHESTRATOR_BASE_URL": live_url,
                },
            )
            if not ok:
                failures.append("Optional live partner stack check")
        else:
            print("\nSkipping live partner stack check: scripts/check_live_partner_stack.py not found.")
    else:
        print("\nSkipping live partner stack check: TRADE_ORCHESTRATOR_BASE_URL is not set.")

    print("\n" + "=" * 90)
    print("BACKEND SMOKE SUITE SUMMARY")
    print("=" * 90)

    if failures:
        print("FAILED CHECKS:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("ALL BACKEND SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
