# Design notes: MCP on Appwrite Functions

## Why not the official Streamable HTTP ASGI stack?

Appwrite Functions are short-lived request/response workers (Gunicorn + aiohttp for Python). They do **not** support:

- Long-lived SSE streams
- uvicorn / Starlette `StreamableHTTPSessionManager`
- Multi-message sessions across executions

The Streamable HTTP spec allows **JSON-mode** responses: one `application/json` body per POST. That is what this template implements.

## Keep vs drop

| Keep on Function | Don't try on Function |
| --- | --- |
| Tool catalog + `tools/call` | uvicorn / Starlette ASGI |
| API key → Appwrite REST | SSE Streamable HTTP |
| JSON request/response | OAuth resource-server + `/.well-known` |
| Short tool calls (&lt;30s) | Long multi-step agent loops in one request |

## Practical constraints

1. **30s hard timeout** on Function domains — soft-cap tools with `MCP_TOOL_TIMEOUT` (default 25).
2. **No streaming** — one buffered response per execution.
3. **Cold start** — module-level lazy singletons are fine for warm reuse; never store per-session state.
4. **Auth** — prefer open demo or bearer token; OAuth discovery is a poor fit here.
5. **Sites** don't help — this is Functions-only.

## Protocol surface

Supported methods:

- `initialize` / `notifications/initialized`
- `ping`
- `tools/list` / `tools/call`
- `prompts/list` / `resources/list` / `resources/templates/list` (empty)

HTTP:

- `POST` → JSON-RPC
- `OPTIONS` → CORS 204
- `GET` / `DELETE` → 405 (no SSE, no sessions)

Notifications return **HTTP 202** with an empty body (not 204).

## Layout tip

Name your tools module `app.py` (or anything other than `server.py`). Open Runtimes’ Python image already loads a top-level `server` module; importing `from server import …` will collide and return HTTP 503 at runtime.

## Statelessness

If the server never returns `Mcp-Session-Id`, clients must not send one. Each Function execution is independent. Pass everything a tool needs via arguments or Function env / dynamic API key headers.
