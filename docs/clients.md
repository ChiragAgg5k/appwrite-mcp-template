# Client configuration

## Cursor / Claude Desktop — remote Streamable HTTP

After deploy, put the Function domain in `mcp.json`:

```json
{
  "mcpServers": {
    "appwrite-hosted": {
      "url": "https://mcp-example.sgp.appwrite.run"
    }
  }
}
```

### With bearer auth

Set Function env:

```
MCP_AUTH_MODE=bearer
MCP_AUTH_TOKEN=your-long-random-secret
```

Client:

```json
{
  "mcpServers": {
    "appwrite-hosted": {
      "url": "https://mcp-example.sgp.appwrite.run",
      "headers": {
        "Authorization": "Bearer your-long-random-secret"
      }
    }
  }
}
```

## Local development

```bash
python scripts/dev.py 8787
```

```json
{
  "mcpServers": {
    "appwrite-hosted-local": {
      "url": "http://127.0.0.1:8787"
    }
  }
}
```

## stdio bridge (fallback)

For clients that only speak stdio MCP:

```json
{
  "mcpServers": {
    "appwrite-hosted": {
      "command": "python",
      "args": ["/absolute/path/to/scripts/bridge.py"],
      "env": {
        "MCP_URL": "https://mcp-example.sgp.appwrite.run",
        "MCP_AUTH_TOKEN": ""
      }
    }
  }
}
```

## Smoke test

```bash
./scripts/smoke.sh https://mcp-example.sgp.appwrite.run
```
