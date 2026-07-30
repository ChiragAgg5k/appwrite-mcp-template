# Example tools

Copy a function body into [`functions/mcp/src/app.py`](../functions/mcp/src/app.py), keep your existing `server = MCPServer(...)`, then:

```bash
appwrite push functions --with-variables
```

| File | Shows |
|------|--------|
| [`fetch_url.py`](fetch_url.py) | Outbound HTTPS, dict return values |
| [`appwrite_users.py`](appwrite_users.py) | `ctx: Context` + dynamic API key (`users.read` scope) |

Inject Appwrite request headers with the SDK context type (not a bare `context` name):

```python
from mcp.server.mcpserver import Context

@server.tool(description="...")
def my_tool(ctx: Context, query: str) -> str:
    api_key = (ctx.headers or {}).get("x-appwrite-key")
    ...
```
