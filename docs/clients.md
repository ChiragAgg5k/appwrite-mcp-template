# Client configuration

## Claude Code / Claude CLI

```bash
claude mcp add --transport http my-mcp https://<your-function>.appwrite.run
```

With bearer auth:

```bash
claude mcp add --transport http my-mcp https://<your-function>.appwrite.run \
  --header "Authorization: Bearer your-long-random-secret"
```

## Cursor / Claude Desktop — remote Streamable HTTP

After deploy, put the Function domain in `mcp.json`:

```json
{
  "mcpServers": {
    "my-mcp": {
      "url": "https://<your-function>.appwrite.run"
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
    "my-mcp": {
      "url": "https://<your-function>.appwrite.run",
      "headers": {
        "Authorization": "Bearer your-long-random-secret"
      }
    }
  }
}
```

## Local development

```bash
uv run python scripts/dev.py 8787
```

```bash
claude mcp add --transport http my-mcp-local http://127.0.0.1:8787
```

```json
{
  "mcpServers": {
    "my-mcp-local": {
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
    "my-mcp": {
      "command": "python",
      "args": ["/absolute/path/to/scripts/bridge.py"],
      "env": {
        "MCP_URL": "https://<your-function>.appwrite.run",
        "MCP_AUTH_TOKEN": ""
      }
    }
  }
}
```

## Smoke test

```bash
./scripts/smoke.sh https://<your-function>.appwrite.run
```
