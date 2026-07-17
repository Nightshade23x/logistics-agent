from __future__ import annotations

import os
import subprocess
import sys


def run_check(name: str, command: list[str], env_overrides: dict[str, str | None] | None = None) -> bool:
    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()


    # Quick checks should never accidentally hit the real live orchestrator.
    env.pop("TRADE_ORCHESTRATOR_BASE_URL", None)

    if env_overrides:
        for key, value in env_overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value

    result = subprocess.run(command, env=env)
    if result.returncode == 0:
        print(f"PASS: {name}")
        return True

    print(f"FAIL: {name}")
    return False


def main() -> int:
    checks = [
        (
            "Compile core backend files",
            [
                sys.executable,
                "-m",
                "py_compile",
                "app/user_agent.py",
                "app/partner_review_service.py",
                "app/partner_adapters/trade_orchestrator_client.py",
                "app/trader_adapter.py",
            ],
            {},
        ),
        (
            "User Agent regression tests",
            [sys.executable, "scripts/test_user_agent.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": None,
            },
        ),
        (
            "Partner review observability",
            [sys.executable, "scripts/test_partner_review_observability.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": None,
            },
        ),
        (
            "Partner payload enrichment",
            [sys.executable, "scripts/test_partner_payload_enrichment.py"],
            {
                "USE_TRAINED_ROUTER": "1",
                "ENABLE_TRADER_AGENT": "1",
            },
        ),
    ]

    failed: list[str] = []

    for name, command, env_overrides in checks:
        if not run_check(name, command, env_overrides):
            failed.append(name)

    print("\n" + "=" * 80)
    print("QUICK BACKEND CHECK SUMMARY")
    print("=" * 80)

    if failed:
        print("FAILED CHECKS:")
        for name in failed:
            print(f"- {name}")
        return 1

    print("ALL QUICK BACKEND CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
