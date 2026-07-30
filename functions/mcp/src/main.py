"""Appwrite Function entrypoint — thin adapter around mcp_lite."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure sibling modules (app, mcp_lite) resolve under Appwrite's entrypoint layout.
# Note: never name a user module `server` — Open Runtimes already ships server.py.
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app import server  # noqa: E402
from mcp_lite import handle_http  # noqa: E402


async def main(context):
    return await handle_http(server, context)
