# Example tools

Copy a function body into [`functions/mcp/src/app.py`](../functions/mcp/src/app.py), keep your existing `server = MCPServer(...)`, then:

```bash
appwrite --force push functions --with-variables
```

| File | Shows |
|------|--------|
| [`fetch_url.py`](fetch_url.py) | Outbound HTTPS, dict return values |
| [`appwrite_users.py`](appwrite_users.py) | `context` param + dynamic API key (`users.read` scope) |
