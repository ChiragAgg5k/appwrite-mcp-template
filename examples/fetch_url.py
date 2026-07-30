"""
Copy-paste example: fetch a public URL over HTTPS.

Paste the `@server.tool` function into `functions/mcp/src/app.py`
(keep your existing `server = MCPServer(...)` and imports).
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

# Assumes `server` is already defined in app.py:
#   from mcp.server.mcpserver import MCPServer
#   server = MCPServer(...)


@server.tool(  # noqa: F821 — paste into app.py where `server` exists
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
