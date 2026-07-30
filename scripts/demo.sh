#!/usr/bin/env bash
# Pretty MCP demo against a Streamable HTTP endpoint (for README recording).
set -euo pipefail

URL="${1:-https://mcp-example.sgp.appwrite.run}"
URL="${URL%/}"

post() {
  local body="$1"
  curl -sS -X POST "$URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d "$body"
}

echo "$ curl -X POST $URL"
echo
echo "# initialize"
post '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"demo","version":"0.1.0"}}}' \
  | jq -c '{serverInfo: .result.serverInfo, protocolVersion: .result.protocolVersion}'
echo
echo "# tools/list"
post '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | jq -c '[.result.tools[] | {name, description}]'
echo
echo "# tools/call echo"
post '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"text":"hello from Appwrite"}}}' \
  | jq -c '.result'
echo
echo "# tools/call add"
post '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"add","arguments":{"a":21,"b":21}}}' \
  | jq -c '.result'
echo
echo "OK — hosted MCP on Appwrite Functions"
