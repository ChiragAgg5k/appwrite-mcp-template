#!/usr/bin/env bash
# Smoke-test a hosted (or local) MCP JSON endpoint.
set -euo pipefail

URL="${1:?Usage: $0 https://<function-domain>}"
URL="${URL%/}"

have_ax=0
if command -v ax >/dev/null 2>&1; then
  have_ax=1
fi

post() {
  local body="$1"
  if [[ "$have_ax" -eq 1 ]]; then
    ax --body -X POST -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d "$body" "$URL"
  else
    curl -sS -X POST -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d "$body" "$URL"
  fi
}

post_status() {
  local body="$1"
  curl -sS -o /tmp/mcp-smoke-body.json -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d "$body" "$URL"
}

echo "== initialize =="
INIT=$(post '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1.0"}}}')
echo "$INIT" | head -c 800
echo
echo "$INIT" | grep -q '"serverInfo"' || { echo "FAIL: no serverInfo"; exit 1; }

echo "== notifications/initialized (expect HTTP 202) =="
CODE=$(post_status '{"jsonrpc":"2.0","method":"notifications/initialized"}')
echo "status=$CODE"
[[ "$CODE" == "202" ]] || { echo "FAIL: expected 202"; exit 1; }

echo "== tools/list =="
LIST=$(post '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}')
echo "$LIST" | head -c 1200
echo
echo "$LIST" | grep -q '"tools"' || { echo "FAIL: no tools"; exit 1; }

echo "== tools/call echo =="
CALL=$(post '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"text":"pong"}}}')
echo "$CALL"
echo "$CALL" | grep -q 'pong' || { echo "FAIL: echo mismatch"; exit 1; }

echo "== GET (expect 405) =="
GCODE=$(curl -sS -o /dev/null -w "%{http_code}" "$URL")
echo "status=$GCODE"
[[ "$GCODE" == "405" ]] || { echo "WARN: expected 405 for GET, got $GCODE"; }

echo "OK — MCP endpoint looks healthy: $URL"
