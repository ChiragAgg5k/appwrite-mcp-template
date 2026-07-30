# Appwrite Hosted MCP Template

Stateless [MCP](https://modelcontextprotocol.io/) server that runs on **Appwrite Functions** — JSON-RPC over HTTPS, no SSE, no ASGI stack.

Edit [`functions/mcp/src/app.py`](functions/mcp/src/app.py), push with the Appwrite CLI, paste the function domain into Cursor/`mcp.json`.

## Live example

Deployed to project `chirag-project-prod` (sgp):

**https://mcp-example.sgp.appwrite.run**

```json
{
  "mcpServers": {
    "appwrite-hosted": {
      "url": "https://mcp-example.sgp.appwrite.run"
    }
  }
}
```

Tools: `echo`, `fetch_url`, `list_users`.

## Quickstart

```bash
# 1. Point appwrite.config.json at your project
# 2. Copy env and push (use the global Cloud endpoint — not a regional one)
cp functions/mcp/.env.example functions/mcp/.env
appwrite client --endpoint https://cloud.appwrite.io/v1 --project-id <your-project>
appwrite --force push functions --function-id mcp-example --with-variables

# 3. Get / create the domain
appwrite proxy list-rules
# or: appwrite proxy create-function-rule --domain mcp-example.sgp.appwrite.run --function-id mcp-example

# 4. Smoke-test
./scripts/smoke.sh https://mcp-example.sgp.appwrite.run
```

## Add your own tools

```python
# functions/mcp/src/app.py
from mcp_lite import MCPServer

server = MCPServer(name="my-mcp", version="0.1.0")

@server.tool(description="Do something useful.")
def my_tool(query: str) -> str:
    return f"got: {query}"
```

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

## Constraints (Functions)

- **30s** hard timeout on domain executions — keep tools under ~25s (`MCP_TOOL_TIMEOUT`)
- **No SSE** — one JSON response per request (spec-compliant Streamable HTTP JSON mode)
- **Stateless** — no sessions, no progress streaming, no sampling

See [docs/design.md](docs/design.md) and [docs/clients.md](docs/clients.md).
