"""
Example hosted MCP tools for Appwrite Functions.

Edit this file (`app.py`) when building your own server.
Do not name it `server.py` — that conflicts with the Open Runtimes runtime module.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from mcp_lite import MCPServer

server = MCPServer(
    name=os.environ.get("MCP_SERVER_NAME") or "appwrite-hosted-mcp",
    version="0.1.0",
)


@server.tool(description="Echo text back — verifies the MCP transport works end-to-end.")
def echo(text: str) -> str:
    return text


@server.tool(
    description=(
        "Fetch a public URL over HTTPS and return up to max_bytes of the response body. "
        "Useful for proving outbound network from the Function."
    )
)
def fetch_url(url: str, max_bytes: int = 20000) -> dict[str, Any]:
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")

    max_bytes = max(1, min(int(max_bytes), 200_000))
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "appwrite-hosted-mcp/0.1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read(max_bytes + 1)
            truncated = len(raw) > max_bytes
            body = raw[:max_bytes]
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                text = body.decode(charset, errors="replace")
            except LookupError:
                text = body.decode("utf-8", errors="replace")
            return {
                "status": getattr(resp, "status", 200),
                "content_type": resp.headers.get("Content-Type"),
                "truncated": truncated,
                "bytes": len(body),
                "body": text,
            }
    except urllib.error.HTTPError as exc:
        err_body = exc.read(max_bytes).decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {err_body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed: {exc.reason}") from exc


@server.tool(
    description=(
        "List users in this Appwrite project using the Function's dynamic API key "
        "(requires scopes: users.read). Optional search filters by name/email."
    )
)
def list_users(context, limit: int = 25, search: str | None = None) -> dict[str, Any]:
    limit = max(1, min(int(limit), 100))
    headers = context.req.headers or {}
    api_key = headers.get("x-appwrite-key") or os.environ.get("APPWRITE_API_KEY")
    project = (
        headers.get("x-appwrite-project")
        or os.environ.get("APPWRITE_FUNCTION_PROJECT_ID")
        or os.environ.get("APPWRITE_PROJECT_ID")
    )
    endpoint = (
        os.environ.get("APPWRITE_ENDPOINT")
        or os.environ.get("APPWRITE_FUNCTION_API_ENDPOINT")
        or "https://cloud.appwrite.io/v1"
    ).rstrip("/")

    if not api_key:
        raise RuntimeError(
            "No API key available. Deploy with scopes including users.read "
            "so Appwrite injects x-appwrite-key, or set APPWRITE_API_KEY."
        )
    if not project:
        raise RuntimeError("Missing project id (x-appwrite-project / APPWRITE_FUNCTION_PROJECT_ID).")

    # Appwrite REST Query encoding: limit(N)
    q_limit = urllib.parse.quote(f"limit({limit})")
    url = f"{endpoint}/users?queries[]={q_limit}"
    if search:
        url += f"&search={urllib.parse.quote(search)}"

    req = urllib.request.Request(
        url,
        headers={
            "X-Appwrite-Project": project,
            "X-Appwrite-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "appwrite-hosted-mcp/0.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Appwrite Users API HTTP {exc.code}: {err[:800]}") from exc

    users = [
        {
            "$id": u.get("$id"),
            "name": u.get("name"),
            "email": u.get("email"),
            "status": u.get("status"),
        }
        for u in data.get("users", [])
    ]
    return {"total": data.get("total", len(users)), "users": users}
