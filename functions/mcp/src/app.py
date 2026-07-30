"""
Example hosted MCP tools for Appwrite Functions.

Edit this file when building your own server.
Do not name it `server.py` — that conflicts with the Open Runtimes runtime module.

See `examples/` in the repo root for more tool patterns (fetch_url, Appwrite Users API).
"""

from __future__ import annotations

import os

from mcp_lite import MCPServer

server = MCPServer(
    name=os.environ.get("MCP_SERVER_NAME") or "appwrite-hosted-mcp",
    version="0.1.0",
)


@server.tool(description="Echo text back — verifies the MCP transport works end-to-end.")
def echo(text: str) -> str:
    return text


@server.tool(description="Add two numbers.")
def add(a: float, b: float) -> float:
    return a + b
