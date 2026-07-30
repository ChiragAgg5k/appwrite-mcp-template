# Design notes: MCP on Appwrite Functions

## Why not `streamable_http_app()`?

Appwrite Functions are short-lived request/response workers (gunicorn + aiohttp). They do **not** support:

- Long-lived SSE streams
- A Starlette/uvicorn lifespan that starts `StreamableHTTPSessionManager`
- Multi-message sessions across executions

The official SDK's `MCPServer.streamable_http_app()` wires `session_manager.run()` into the Starlette lifespan. Without that lifespan, every request raises:

```
RuntimeError: Task group is not initialized. Make sure to use run().
```

That check fires even with `stateless_http=True` / `json_response=True`. The ASGI path is a dead end on Functions.

## What we do instead

A thin Appwrite adapter ([`functions/mcp/src/appwrite_mcp/`](../functions/mcp/src/appwrite_mcp/)) drives the SDK's lower-level entry points with a fully buffered request/response:

| Protocol era | Header | Dispatch |
| --- | --- | --- |
| Legacy handshake (`2024-11-05` … `2025-11-25`) | absent or handshake version | `serve_one` + born-ready `Connection.from_envelope` |
| Modern sessionless (`2026-07-28`) | `MCP-Protocol-Version: 2026-07-28` | `handle_modern_request` (ASGI scope/receive/send shim) |

Cursor and Claude Code today speak the legacy handshake — that is why both legs exist. Pin `mcp==2.0.0` exactly: `handle_modern_request` and `MCPServer._lowlevel_server` are private and can move.

## Keep vs drop

| Keep on Function | Don't try on Function |
| --- | --- |
| Tool catalog + `tools/call` | uvicorn / Starlette lifespan |
| Official SDK schema derivation | SSE Streamable HTTP |
| API key → Appwrite REST via `ctx.headers` | OAuth resource-server + `/.well-known` |
| Short tool calls (&lt;30s) | Long multi-step agent loops in one request |
| JSON request/response | Progress streaming / sampling back-channel |

## Practical constraints

1. **30s hard timeout** on Function domains — soft-cap the whole request with `MCP_TOOL_TIMEOUT` (default 25).
2. **No streaming** — one buffered response per execution. Progress notifications are dropped.
3. **Cold start** — `mcp` pulls in pydantic, starlette, jsonschema (~10 MB of musllinux wheels). Fine on Cloud's build size limits; first request pays the import cost.
4. **Auth** — prefer open demo or bearer token; OAuth discovery is a poor fit here.
5. **Exception text** — tool failures become `isError: true` results. Detail is stripped unless `MCP_DEBUG=1`.
6. **Sites** don't help — this is Functions-only.

## Protocol surface

Supported methods (via the SDK):

- `initialize` / `notifications/initialized`
- `ping`
- `tools/list` / `tools/call`
- `prompts/list` / `resources/list` / `resources/templates/list` (empty until you register some)

HTTP:

- `POST` → JSON-RPC
- `OPTIONS` → CORS 204
- `GET` / `DELETE` → 405 (no SSE, no sessions)

Notifications return **HTTP 202** with an empty body.

## Layout tip

Name your tools module `app.py` (or anything other than `server.py`). Open Runtimes’ Python image already loads a top-level `server` module; importing `from server import …` will collide and return HTTP 503 at runtime.

Do not name the adapter package `mcp` either — that would shadow the installed SDK on `sys.path`.

## Statelessness

If the server never returns `Mcp-Session-Id`, clients must not send one. Each Function execution is independent. Pass everything a tool needs via arguments, Function env, or inbound headers (`ctx: Context` → `ctx.headers`, including Appwrite's dynamic `x-appwrite-key`).
