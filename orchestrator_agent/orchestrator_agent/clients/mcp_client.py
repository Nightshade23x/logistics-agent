"""MCP client wrappers for Risk, Compliance, and Trader agents.

Each agent lives in its own git worktree (separate branch) with its own
venv and a nested inner package folder (e.g. agent-risk\risk_agent\risk_agent\).
This client spawns each one as a subprocess using that worktree's own
Python interpreter, with cwd set to the outer package folder so
`python -m risk_agent.server` resolves correctly.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv



class McpAgentClient:
    def __init__(self, python_exe: str, module: str, cwd: str) -> None:
        self._params = StdioServerParameters(
            command=python_exe,
            args=["-m", module],
            cwd=cwd,
        )

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return json.loads(result.content[0].text)

    def call_tool_sync(self, tool_name: str, arguments: dict) -> dict:
        return asyncio.run(self.call_tool(tool_name, arguments))


_GH_ROOT = r"C:\Users\avish\OneDrive\Desktop\GitHub Projects"


load_dotenv()


def _resolve_agent_cwd(env_name: str, package_name: str) -> str:
    """Resolve agent cwd for both separate worktree and combined-repo layouts."""
    root = Path(os.environ[env_name]).resolve()

    # Combined repo layout:
    #   <repo>/risk_agent/risk_agent/server.py
    # env points to <repo>/risk_agent, cwd should be <repo>/risk_agent.
    if (root / package_name / "server.py").exists():
        return str(root)

    # Separate worktree layout:
    #   <worktree>/risk_agent/risk_agent/server.py
    # env points to <worktree>, cwd should be <worktree>/risk_agent.
    if (root / package_name / package_name / "server.py").exists():
        return str(root / package_name)

    # Backward-compatible fallback.
    return str(root / package_name)


def _resolve_agent_python(env_name: str, python_env_name: str) -> str:
    """Use explicit env python, per-agent venv python, or current Python as fallback."""
    explicit_python = os.environ.get(python_env_name)
    if explicit_python and Path(explicit_python).exists():
        return explicit_python

    root = Path(os.environ[env_name]).resolve()
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)

    return sys.executable


_RISK_CWD = _resolve_agent_cwd("RISK_AGENT_DIR", "risk_agent")
_COMPLIANCE_CWD = _resolve_agent_cwd("COMPLIANCE_AGENT_DIR", "compliance_agent")
_TRADER_CWD = _resolve_agent_cwd("TRADER_AGENT_DIR", "trader_agent")

_RISK_PYTHON = _resolve_agent_python("RISK_AGENT_DIR", "RISK_AGENT_PYTHON")
_COMPLIANCE_PYTHON = _resolve_agent_python("COMPLIANCE_AGENT_DIR", "COMPLIANCE_AGENT_PYTHON")
_TRADER_PYTHON = _resolve_agent_python("TRADER_AGENT_DIR", "TRADER_AGENT_PYTHON")


def build_risk_client() -> McpAgentClient:
    return McpAgentClient(python_exe=_RISK_PYTHON, module="risk_agent.server", cwd=_RISK_CWD)


def build_compliance_client() -> McpAgentClient:
    return McpAgentClient(
        python_exe=_COMPLIANCE_PYTHON, module="compliance_agent.server", cwd=_COMPLIANCE_CWD
    )


def build_trader_client() -> McpAgentClient:
    return McpAgentClient(python_exe=_TRADER_PYTHON, module="trader_agent.server", cwd=_TRADER_CWD)