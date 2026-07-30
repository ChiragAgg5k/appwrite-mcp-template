#!/usr/bin/env python3
"""Local HTTP server wrapping the same Appwrite MCP handler (stdlib only)."""

from __future__ import annotations

import asyncio
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "functions" / "mcp" / "src"
sys.path.insert(0, str(SRC))

from mcp_lite import handle_http  # noqa: E402
from app import server  # noqa: E402


class FakeRes:
    def binary(self, body, statusCode=200, headers=None):
        return {"body": body, "statusCode": statusCode, "headers": dict(headers or {})}

    def text(self, body, statusCode=200, headers=None):
        return self.binary(body.encode("utf-8"), statusCode, headers)

    def json(self, obj, statusCode=200, headers=None):
        headers = dict(headers or {})
        headers["content-type"] = "application/json"
        return self.text(json.dumps(obj, separators=(",", ":")), statusCode, headers)

    def empty(self):
        return self.text("", 204, {})


class FakeReq:
    def __init__(self, handler: BaseHTTPRequestHandler, body: bytes):
        self.method = handler.command
        self.path = handler.path.split("?", 1)[0]
        self.headers = {k.lower(): v for k, v in handler.headers.items()}
        self.body_binary = body
        self.query = {}
        self.query_string = ""

    @property
    def body_text(self):
        return self.body_binary.decode("utf-8")

    @property
    def body_json(self):
        return json.loads(self.body_text)

    @property
    def body(self):
        ct = self.headers.get("content-type", "").lower()
        if ct.startswith("application/json"):
            return self.body_json if self.body_binary else {}
        return self.body_text


class Ctx:
    def __init__(self, req):
        self.req = req
        self.res = FakeRes()

    def log(self, *a):
        print("[log]", *a, file=sys.stderr)

    def error(self, *a):
        print("[error]", *a, file=sys.stderr)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        ctx = Ctx(FakeReq(self, body))
        result = asyncio.run(handle_http(server, ctx))
        status = result["statusCode"]
        headers = result.get("headers") or {}
        raw = result.get("body") or b""
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        if "content-type" not in {h.lower() for h in headers}:
            if raw:
                self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if raw and self.command != "HEAD":
            self.wfile.write(raw)

    def do_OPTIONS(self):
        self._handle()

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_DELETE(self):
        self._handle()


def main():
    host = "127.0.0.1"
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Local MCP listening on http://{host}:{port}", file=sys.stderr)
    print("Configure Cursor with: {\"url\": \"http://127.0.0.1:%d\"}" % port, file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye", file=sys.stderr)


if __name__ == "__main__":
    main()
