"""
Copy-paste example: list users via the Appwrite Users API.

Requires Function scopes including `users.read` (see appwrite.config.json).
Appwrite injects `x-appwrite-key` (dynamic API key) on each execution.

Paste the `@server.tool` function into `functions/mcp/src/app.py`
(keep your existing `server = MCPServer(...)` and imports).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Assumes `server` is already defined in app.py:
#   from mcp_lite import MCPServer
#   server = MCPServer(...)


@server.tool(  # noqa: F821 — paste into app.py where `server` exists
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
        raise RuntimeError(
            "Missing project id (x-appwrite-project / APPWRITE_FUNCTION_PROJECT_ID)."
        )

    # Appwrite Query encoding (JSON): Query.limit(N) → {"method":"limit","values":[N]}
    # Keep the literal `queries[]` key — urllib.urlencode would turn [] into %5B%5D.
    q_limit = urllib.parse.quote(
        json.dumps({"method": "limit", "values": [limit]}, separators=(",", ":")),
        safe="",
    )
    url = f"{endpoint}/users?queries[]={q_limit}"
    if search:
        url += f"&search={urllib.parse.quote(search, safe='')}"

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
