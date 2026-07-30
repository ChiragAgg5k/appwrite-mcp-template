"""End-to-end MCP handshake tests against the Appwrite adapter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcp.server.mcpserver import Context, MCPServer

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "functions" / "mcp" / "src"
sys.path.insert(0, str(SRC))

from appwrite_mcp import handle_http  # noqa: E402
from tests.conftest import FakeContext, FakeRequest, decode_body  # noqa: E402

MODERN = "2026-07-28"
PVK = "io.modelcontextprotocol/protocolVersion"
CCK = "io.modelcontextprotocol/clientCapabilities"
CIK = "io.modelcontextprotocol/clientInfo"


def _server() -> MCPServer:
    s = MCPServer(name="test-mcp", version="0.1.0", instructions="test")

    @s.tool(description="Echo")
    def echo(text: str) -> str:
        return text

    @s.tool(description="Always fails")
    def boom() -> str:
        raise RuntimeError("kaboom")

    @s.tool(description="Read inbound headers")
    def whoami(ctx: Context) -> dict:
        headers = ctx.headers or {}
        return {
            "api_key": headers.get("x-appwrite-key"),
            "protocol_version": ctx.protocol_version,
        }

    return s


async def _call(server: MCPServer, method: str = "POST", body=None, headers=None, **kw):
    ctx = FakeContext(FakeRequest(method=method, body=body, headers=headers, **kw))
    return await handle_http(server, ctx)


@pytest.mark.asyncio
async def test_initialize_handshake():
    server = _server()
    result = await _call(
        server,
        body={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        },
    )
    assert result["statusCode"] == 200
    payload = decode_body(result)
    assert payload["result"]["protocolVersion"] == "2025-06-18"
    assert "tools" in payload["result"]["capabilities"]
    assert payload["result"]["serverInfo"]["name"] == "test-mcp"


@pytest.mark.asyncio
async def test_notification_initialized_returns_202():
    server = _server()
    result = await _call(
        server,
        body={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert result["statusCode"] == 202
    assert result["body"] == b""


@pytest.mark.asyncio
async def test_tools_list_and_call():
    server = _server()
    listed = await _call(
        server,
        body={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    tools = decode_body(listed)["result"]["tools"]
    names = {t["name"] for t in tools}
    assert names == {"echo", "boom", "whoami"}
    echo = next(t for t in tools if t["name"] == "echo")
    assert "text" in echo["inputSchema"]["required"]

    called = await _call(
        server,
        body={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "hi"}},
        },
    )
    payload = decode_body(called)
    assert payload["result"]["content"][0]["text"] == "hi"
    assert payload["result"].get("isError") is not True


@pytest.mark.asyncio
async def test_tool_error_is_error_true():
    server = _server()
    called = await _call(
        server,
        body={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "boom", "arguments": {}},
        },
    )
    payload = decode_body(called)
    assert payload["result"]["isError"] is True
    # Sanitized unless MCP_DEBUG — detail stripped
    text = payload["result"]["content"][0]["text"]
    assert "Error executing tool boom" in text
    assert "kaboom" not in text


@pytest.mark.asyncio
async def test_tool_error_leaks_when_debug(monkeypatch):
    monkeypatch.setenv("MCP_DEBUG", "1")
    server = _server()
    called = await _call(
        server,
        body={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "boom", "arguments": {}},
        },
    )
    payload = decode_body(called)
    assert "kaboom" in payload["result"]["content"][0]["text"]


@pytest.mark.asyncio
async def test_get_and_delete_return_405():
    server = _server()
    for method in ("GET", "DELETE"):
        result = await _call(server, method=method, body=None)
        assert result["statusCode"] == 405


@pytest.mark.asyncio
async def test_options_cors():
    server = _server()
    result = await _call(server, method="OPTIONS")
    assert result["statusCode"] == 204
    assert result["headers"].get("Access-Control-Allow-Origin") == "*"


@pytest.mark.asyncio
async def test_bearer_auth_required(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_MODE", "bearer")
    monkeypatch.setenv("MCP_AUTH_TOKEN", "secret-token")
    server = _server()

    denied = await _call(
        server,
        body={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    assert denied["statusCode"] == 401

    ok = await _call(
        server,
        body={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": "Bearer secret-token"},
    )
    assert ok["statusCode"] == 200
    assert decode_body(ok)["result"] == {}


@pytest.mark.asyncio
async def test_unknown_method():
    server = _server()
    result = await _call(
        server,
        body={"jsonrpc": "2.0", "id": 9, "method": "foo/bar"},
    )
    payload = decode_body(result)
    assert payload["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_malformed_json():
    server = _server()
    result = await _call(server, body="{not-json")
    assert result["statusCode"] == 400
    assert decode_body(result)["error"]["code"] == -32700


@pytest.mark.asyncio
async def test_ping_and_empty_lists():
    server = _server()
    for method, key in (
        ("ping", None),
        ("prompts/list", "prompts"),
        ("resources/list", "resources"),
    ):
        result = await _call(
            server,
            body={"jsonrpc": "2.0", "id": 1, "method": method, "params": {}},
        )
        payload = decode_body(result)
        if key:
            assert payload["result"][key] == []
        else:
            assert payload["result"] == {}


@pytest.mark.asyncio
async def test_context_headers_injection():
    server = _server()
    called = await _call(
        server,
        body={
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "whoami", "arguments": {}},
        },
        headers={"x-appwrite-key": "dyn-key-abc"},
    )
    payload = decode_body(called)
    structured = payload["result"].get("structuredContent") or {}
    # SDK may wrap dict returns; also check text content
    if structured.get("api_key"):
        assert structured["api_key"] == "dyn-key-abc"
    else:
        text = payload["result"]["content"][0]["text"]
        assert "dyn-key-abc" in text


@pytest.mark.asyncio
async def test_modern_tools_list():
    server = _server()
    result = await _call(
        server,
        body={
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/list",
            "params": {"_meta": {PVK: MODERN, CCK: {}}},
        },
        headers={
            "mcp-protocol-version": MODERN,
            "mcp-method": "tools/list",
            "accept": "application/json, text/event-stream",
        },
    )
    assert result["statusCode"] == 200
    payload = decode_body(result)
    names = {t["name"] for t in payload["result"]["tools"]}
    assert "echo" in names


@pytest.mark.asyncio
async def test_modern_tools_call():
    server = _server()
    result = await _call(
        server,
        body={
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "_meta": {
                    PVK: MODERN,
                    CCK: {},
                    CIK: {"name": "test", "version": "1"},
                },
                "name": "echo",
                "arguments": {"text": "modern-hi"},
            },
        },
        headers={
            "mcp-protocol-version": MODERN,
            "mcp-method": "tools/call",
            "mcp-name": "echo",
            "accept": "application/json, text/event-stream",
        },
    )
    assert result["statusCode"] == 200
    payload = decode_body(result)
    assert payload["result"]["content"][0]["text"] == "modern-hi"
    assert payload["result"].get("isError") is not True
