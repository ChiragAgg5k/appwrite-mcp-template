# MCP JSON-RPC method dispatch (stateless).

from __future__ import annotations

import os
from typing import Any

from .errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    McpError,
    jsonrpc_error,
    jsonrpc_result,
)
from .registry import MCPServer

SUPPORTED_PROTOCOL_VERSIONS = (
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)
DEFAULT_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]


def _server_name(server: MCPServer) -> str:
    return os.environ.get("MCP_SERVER_NAME") or server.name


async def handle_message(server: MCPServer, message: Any) -> dict[str, Any] | None:
    """
    Process one JSON-RPC message.
    Returns a response dict for requests, or None for notifications/responses.
    """
    if not isinstance(message, dict):
        return jsonrpc_error(None, INVALID_REQUEST, "Message must be a JSON object")

    if message.get("jsonrpc") != "2.0":
        return jsonrpc_error(
            message.get("id"),
            INVALID_REQUEST,
            "jsonrpc must be '2.0'",
        )

    # Client -> server response (rare for our tools-only server)
    if "result" in message or "error" in message:
        return None

    method = message.get("method")
    if not isinstance(method, str) or not method:
        return jsonrpc_error(message.get("id"), INVALID_REQUEST, "Missing method")

    params = message.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return jsonrpc_error(message.get("id"), INVALID_PARAMS, "params must be an object")

    req_id = message.get("id", _MISSING)
    is_notification = req_id is _MISSING

    try:
        result = await _dispatch(server, method, params)
    except McpError as exc:
        if is_notification:
            return None
        return jsonrpc_error(req_id, exc.code, exc.message, exc.data)
    except Exception as exc:  # noqa: BLE001
        if is_notification:
            return None
        return jsonrpc_error(req_id, INTERNAL_ERROR, str(exc))

    if is_notification:
        return None
    return jsonrpc_result(req_id, result)


_MISSING = object()


async def _dispatch(server: MCPServer, method: str, params: dict[str, Any]) -> Any:
    if method == "initialize":
        client_version = params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION
        if client_version in SUPPORTED_PROTOCOL_VERSIONS:
            negotiated = client_version
        else:
            negotiated = DEFAULT_PROTOCOL_VERSION
        return {
            "protocolVersion": negotiated,
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": _server_name(server),
                "version": server.version,
            },
            "instructions": (
                "Stateless MCP on Appwrite Functions. "
                "Tools must finish within ~25s (30s domain hard-cap)."
            ),
        }

    if method == "notifications/initialized":
        return {}

    if method == "ping":
        return {}

    if method == "tools/list":
        return {"tools": server.list_tools()}

    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise McpError(INVALID_PARAMS, "tools/call requires params.name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise McpError(INVALID_PARAMS, "params.arguments must be an object")
        return await server.call_tool(name, arguments)

    # Capability probes — empty lists so clients don't hard-fail
    if method == "prompts/list":
        return {"prompts": []}

    if method == "resources/list":
        return {"resources": []}

    if method == "resources/templates/list":
        return {"resourceTemplates": []}

    raise McpError(METHOD_NOT_FOUND, f"Method not found: {method}")
