# Tool registry and MCPServer facade.

from __future__ import annotations

import asyncio
import inspect
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import INVALID_PARAMS, McpError, tool_error_result
from .schema import build_input_schema, normalize_tool_result


@dataclass
class ToolDef:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]
    takes_context: bool = False


@dataclass
class MCPServer:
    name: str = "appwrite-hosted-mcp"
    version: str = "0.1.0"
    tools: dict[str, ToolDef] = field(default_factory=dict)
    # Injected per-request by the transport (Appwrite context)
    _request_context: Any = field(default=None, repr=False)

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
        input_schema: dict[str, Any] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or fn.__name__
            desc = description or (inspect.getdoc(fn) or "").strip() or tool_name
            sig = inspect.signature(fn)
            takes_context = "context" in sig.parameters
            schema = build_input_schema(fn, input_schema)
            self.tools[tool_name] = ToolDef(
                name=tool_name,
                description=desc,
                input_schema=schema,
                handler=fn,
                takes_context=takes_context,
            )
            return fn

        return decorator

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in self.tools.values()
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")

        args = dict(arguments or {})
        if tool.takes_context:
            args["context"] = self._request_context

        timeout = float(os.environ.get("MCP_TOOL_TIMEOUT") or "25")

        try:
            if inspect.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(tool.handler(**args), timeout=timeout)
            else:
                # Run sync tools in a thread so wait_for can cancel the wait
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool.handler, **args),
                    timeout=timeout,
                )
        except asyncio.TimeoutError:
            return tool_error_result(
                f"Tool '{name}' timed out after {timeout}s "
                "(Appwrite function domain hard-cap is 30s)."
            )
        except TypeError as exc:
            return tool_error_result(f"Invalid arguments for '{name}': {exc}")
        except McpError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface to agent as isError
            return tool_error_result(f"Tool '{name}' failed: {exc}")

        return normalize_tool_result(result)
