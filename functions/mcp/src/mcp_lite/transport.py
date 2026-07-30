# Map Appwrite Function req/res <-> MCP Streamable HTTP (JSON mode).

from __future__ import annotations

import json
import os
from typing import Any

from .auth import check_auth
from .errors import PARSE_ERROR, jsonrpc_error
from .protocol import handle_message
from .registry import MCPServer

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS, GET, DELETE",
    "Access-Control-Allow-Headers": (
        "Content-Type, Accept, Authorization, MCP-Protocol-Version, Mcp-Session-Id"
    ),
    "Access-Control-Expose-Headers": "MCP-Protocol-Version",
}


def _merge_headers(*dicts: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for d in dicts:
        out.update(d)
    return out


async def handle_http(server: MCPServer, context: Any) -> Any:
    """
    Appwrite Function entry adapter.
    Returns a context.res.* dict (caller must `return` it).
    """
    req = context.req
    res = context.res
    method = (req.method or "GET").upper()
    headers = {k.lower(): v for k, v in (req.headers or {}).items()}

    server._request_context = context

    if method == "OPTIONS":
        return res.text("", 204, _merge_headers(CORS_HEADERS))

    # Stateless: no SSE GET stream, no session DELETE
    if method in ("GET", "DELETE"):
        body = jsonrpc_error(
            None,
            -32000,
            f"{method} not supported on this stateless MCP endpoint "
            "(JSON-mode Streamable HTTP only; use POST).",
        )
        return res.json(body, 405, _merge_headers(CORS_HEADERS, {"Allow": "POST, OPTIONS"}))

    if method != "POST":
        body = jsonrpc_error(None, -32600, f"Unsupported HTTP method: {method}")
        return res.json(body, 405, _merge_headers(CORS_HEADERS, {"Allow": "POST, OPTIONS"}))

    ok, auth_err = check_auth(headers)
    if not ok and auth_err is not None:
        return res.json(
            auth_err["body"],
            auth_err["status"],
            _merge_headers(CORS_HEADERS, auth_err.get("headers") or {}),
        )

    accept = headers.get("accept", "")
    if accept and "application/json" not in accept and "text/event-stream" not in accept and "*/*" not in accept:
        if os.environ.get("MCP_DEBUG"):
            context.log(f"Unusual Accept header: {accept}")

    raw = req.body_text if hasattr(req, "body_text") else ""
    if not raw and hasattr(req, "body"):
        body_val = req.body
        if isinstance(body_val, (dict, list)):
            raw = json.dumps(body_val)
        elif isinstance(body_val, str):
            raw = body_val
        else:
            raw = ""

    try:
        payload = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError as exc:
        return res.json(
            jsonrpc_error(None, PARSE_ERROR, f"Parse error: {exc}"),
            400,
            _merge_headers(CORS_HEADERS),
        )

    if payload is None:
        return res.json(
            jsonrpc_error(None, PARSE_ERROR, "Empty request body"),
            400,
            _merge_headers(CORS_HEADERS),
        )

    # Batch (legacy / older clients)
    if isinstance(payload, list):
        if not payload:
            return res.json(
                jsonrpc_error(None, -32600, "Empty batch"),
                400,
                _merge_headers(CORS_HEADERS),
            )
        responses = []
        for item in payload:
            resp = await handle_message(server, item)
            if resp is not None:
                responses.append(resp)
        if not responses:
            return res.text("", 202, _merge_headers(CORS_HEADERS))
        return res.json(responses, 200, _merge_headers(CORS_HEADERS))

    response = await handle_message(server, payload)

    # Notification or client response → 202 Accepted, empty body
    if response is None:
        return res.text("", 202, _merge_headers(CORS_HEADERS))

    return res.json(response, 200, _merge_headers(CORS_HEADERS))
