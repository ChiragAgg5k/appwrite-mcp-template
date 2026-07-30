"""Minimal stdlib MCP framework for Appwrite Functions (JSON Streamable HTTP)."""

from .registry import MCPServer
from .transport import handle_http

__all__ = ["MCPServer", "handle_http"]
