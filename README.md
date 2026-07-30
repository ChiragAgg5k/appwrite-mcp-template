# Appwrite Hosted MCP Template

Stateless [MCP](https://modelcontextprotocol.io/) server on **Appwrite Functions** — JSON-RPC over HTTPS, stdlib only. No SSE, no ASGI stack.

Edit [`functions/mcp/src/app.py`](functions/mcp/src/app.py), push with the Appwrite CLI, point your client at the function domain.

## Try the demo

```bash
claude mcp add --transport http appwrite-mcp-demo https://mcp-example.sgp.appwrite.run
```

Or in Cursor / Claude Desktop `mcp.json`:

```json
{
  "mcpServers": {
    "appwrite-mcp-demo": {
      "url": "https://mcp-example.sgp.appwrite.run"
    }
  }
}
```

Demo tools: `echo`, `add`.

## Deploy your own

```bash
# 1. Point the CLI at your project (global Cloud endpoint — not regional)
appwrite client --endpoint https://cloud.appwrite.io/v1 --project-id <your-project>

# 2. Edit appwrite.config.json → set projectId to yours

# 3. Push
cp functions/mcp/.env.example functions/mcp/.env
appwrite --force push functions --with-variables

# 4. Domain
appwrite proxy list-rules
# or: appwrite proxy create-function-rule --domain <name>.<region>.appwrite.run --function-id mcp-example

# 5. Smoke-test
./scripts/smoke.sh https://<your-domain>
```

Then add the domain the same way as the demo:

```bash
claude mcp add --transport http my-mcp https://<your-domain>
```

## Write a tool

```python
# functions/mcp/src/app.py
from mcp_lite import MCPServer

server = MCPServer(name="my-mcp", version="0.1.0")

@server.tool(description="Do something useful.")
def my_tool(query: str) -> str:
    return f"got: {query}"
```

Type hints become the tool `inputSchema`. Add a `context` parameter to read the Appwrite request (headers, dynamic API key). More patterns in [`examples/`](examples/).

Do **not** name the tools module `server.py` — Open Runtimes already ships a top-level `server` module.

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/dev.py          # http://127.0.0.1:8787
./scripts/smoke.sh http://127.0.0.1:8787
.venv/bin/pytest -q
```

## Auth

| Mode | Env | Client header |
|------|-----|---------------|
| Open (default) | `MCP_AUTH_MODE=none` | none |
| Bearer | `MCP_AUTH_MODE=bearer` + `MCP_AUTH_TOKEN=...` | `Authorization: Bearer ...` |

## Limits

- **30s** hard timeout on domain executions — keep tools under ~25s (`MCP_TOOL_TIMEOUT`)
- **No SSE** — one JSON response per request (Streamable HTTP JSON mode)
- **Stateless** — no sessions, no progress streaming, no sampling

See [docs/design.md](docs/design.md) and [docs/clients.md](docs/clients.md).
