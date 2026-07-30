# Derive JSON Schema inputSchema from Python type hints; normalize tool results.

from __future__ import annotations

import inspect
import json
import types
import typing
from enum import Enum
from typing import Any, get_args, get_origin


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Return (inner_type, is_optional)."""
    origin = get_origin(annotation)
    args = get_args(annotation)

    # PEP 604: X | None
    if origin is types.UnionType or origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and type(None) in args:
            return non_none[0], True
        return annotation, type(None) in args

    return annotation, False


def _type_to_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}

    annotation, _ = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is dict or origin is dict:
        return {"type": "object"}
    if annotation is list or origin is list:
        item_schema = _type_to_schema(args[0]) if args else {}
        schema: dict[str, Any] = {"type": "array"}
        if item_schema:
            schema["items"] = item_schema
        return schema

    if origin is typing.Literal:
        values = list(args)
        if values and all(isinstance(v, str) for v in values):
            return {"type": "string", "enum": values}
        if values and all(isinstance(v, bool) for v in values):
            return {"type": "boolean", "enum": values}
        if values and all(isinstance(v, int) and not isinstance(v, bool) for v in values):
            return {"type": "integer", "enum": values}
        return {"enum": values}

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        members = [m.value for m in annotation]
        if members and all(isinstance(v, str) for v in members):
            return {"type": "string", "enum": members}
        return {"enum": members}

    return {}


def build_input_schema(fn: Any, override: dict[str, Any] | None = None) -> dict[str, Any]:
    if override is not None:
        return override

    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn) if hasattr(fn, "__annotations__") else {}

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls", "context"):
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        annotation = hints.get(name, param.annotation)
        prop = _type_to_schema(annotation)
        _, is_optional = _unwrap_optional(annotation)

        if param.default is not inspect.Parameter.empty:
            if param.default is not None:
                prop = {**prop, "default": param.default}
            is_optional = True
        elif not is_optional:
            required.append(name)

        properties[name] = prop

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def normalize_tool_result(value: Any) -> dict[str, Any]:
    """Turn a tool return value into MCP CallToolResult."""
    if value is None:
        return {"content": [{"type": "text", "text": ""}]}

    if isinstance(value, dict) and "content" in value:
        # Already MCP-shaped
        return value

    if isinstance(value, str):
        return {"content": [{"type": "text", "text": value}]}

    if isinstance(value, (dict, list)):
        text = json.dumps(value, separators=(",", ":"), default=str)
        return {
            "content": [{"type": "text", "text": text}],
            "structuredContent": value if isinstance(value, dict) else {"items": value},
        }

    return {"content": [{"type": "text", "text": str(value)}]}
