#!/usr/bin/env python3
"""
stdio MCP <-> HTTPS JSON MCP bridge (Option 2).

Use when a client only speaks stdio MCP but your tools live on an Appwrite Function.

  MCP_URL=https://xxx.sgp.appwrite.run python scripts/bridge.py
  # optional: MCP_AUTH_TOKEN=... for bearer mode
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def post(url: str, message: dict, token: str | None) -> tuple[int, bytes]:
    data = json.dumps(message).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> None:
    url = (os.environ.get("MCP_URL") or "").rstrip("/")
    if not url:
        print("MCP_URL is required", file=sys.stderr)
        sys.exit(1)
    token = os.environ.get("MCP_AUTH_TOKEN") or None

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            continue

        status, body = post(url, message, token)

        # Notifications → remote returns 202 empty; stdio expects no response
        if status == 202 or not body:
            continue

        try:
            text = body.decode("utf-8")
            # Validate JSON
            json.loads(text)
            sys.stdout.write(text + ("\n" if not text.endswith("\n") else ""))
            sys.stdout.flush()
        except Exception as exc:  # noqa: BLE001
            err = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32603, "message": f"Bridge error ({status}): {exc}"},
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
