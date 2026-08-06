"""The server as a real client sees it: a subprocess, over stdio, speaking the protocol.

Every other MCP test calls `call_tool` in process, which checks the tools and skips the thing
phase 2 actually specifies: a LOCAL server over STDIO. A server that works in process and dies
on startup is a server that works nowhere, and nothing else in this suite would notice.

This spawns the installed `bankfile-mcp` entry point, so it also checks the console script and
the packaging, not just the module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.anyio
async def test_the_server_speaks_the_protocol_over_a_real_stdio_pipe() -> None:
    # The installed console script, not `python -m`: this way the test also covers the entry
    # point declared in pyproject.toml, which is what a user's MCP client will actually spawn.
    script = Path(sys.executable).parent / "bankfile-mcp"
    if not script.exists():  # pragma: no cover - only when running outside the project venv
        pytest.skip("bankfile-mcp is not installed in this environment")
    parameters = StdioServerParameters(
        command=str(script), args=["--root", str(REPO)], cwd=str(REPO)
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        initialised = await session.initialize()
        assert initialised.server_info.name == "bankfile"
        # The instructions are the first thing a client shows a model, so the promise that
        # nothing is uploaded belongs there and not only in the README.
        assert "nothing is uploaded" in (initialised.instructions or "")

        tools = await session.list_tools()
        assert {t.name for t in tools.tools} == {
            "read_statement",
            "list_transactions",
            "list_warnings",
        }

        result = await session.call_tool(
            "read_statement", {"path": "tests/fixtures/paired/account-a.sta"}
        )
        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["account"] == "0000123456"
        assert result.structured_content["closing_balance"] == "990.00"
        assert result.structured_content["transaction_count"] == 1

        # A page, through the wire, with its slice metadata intact.
        page = await session.call_tool(
            "list_transactions",
            {"path": "tests/fixtures/mt940/betterplace/sepa_mt9401.sta", "limit": 3},
        )
        assert page.structured_content is not None
        assert len(page.structured_content["entries"]) == 3
        assert page.structured_content["total_matching"] == 97
        assert page.structured_content["truncated"] is True

        # And a refusal, through the wire, still structured rather than a crash.
        refused = await session.call_tool("read_statement", {"path": "../../../etc/passwd"})
        assert refused.structured_content is not None
        assert refused.structured_content["ok"] is False
        assert refused.structured_content["error"]["kind"] == "outside_root"
