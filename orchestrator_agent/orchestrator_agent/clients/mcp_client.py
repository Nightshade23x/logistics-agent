"""MCP client wrappers for Risk, Compliance, and Trader agents.

Each agent lives in its own git worktree (separate branch) with its own
venv and a nested inner package folder (e.g. agent-risk\risk_agent\risk_agent\).
This client spawns each one as a subprocess using that worktree's own
Python interpreter, with cwd set to the outer package folder so
`python -m risk_agent.server` resolves correctly.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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

_RISK_CWD = fr"{_GH_ROOT}\agent-risk\risk_agent"
_COMPLIANCE_CWD = fr"{_GH_ROOT}\agent-compliance\compliance_agent"
_TRADER_CWD = fr"{_GH_ROOT}\agent-trader\trader_agent"

_RISK_PYTHON = fr"{_GH_ROOT}\agent-risk\.venv\Scripts\python.exe"
_COMPLIANCE_PYTHON = fr"{_GH_ROOT}\agent-compliance\.venv\Scripts\python.exe"
_TRADER_PYTHON = fr"{_GH_ROOT}\agent-trader\.venv\Scripts\python.exe"


def build_risk_client() -> McpAgentClient:
    return McpAgentClient(python_exe=_RISK_PYTHON, module="risk_agent.server", cwd=_RISK_CWD)


def build_compliance_client() -> McpAgentClient:
    return McpAgentClient(
        python_exe=_COMPLIANCE_PYTHON, module="compliance_agent.server", cwd=_COMPLIANCE_CWD
    )


def build_trader_client() -> McpAgentClient:
    return McpAgentClient(python_exe=_TRADER_PYTHON, module="trader_agent.server", cwd=_TRADER_CWD)