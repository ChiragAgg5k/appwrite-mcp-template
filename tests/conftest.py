"""Fake Appwrite Function context matching the Python runtime snake_case API."""

from __future__ import annotations

import json
from typing import Any


class FakeRequest:
    def __init__(
        self,
        method: str = "POST",
        body: Any = None,
        headers: dict[str, str] | None = None,
        path: str = "/",
        query: dict[str, str] | None = None,
    ):
        self.method = method
        self.path = path
        self.query = query or {}
        self.query_string = "&".join(f"{k}={v}" for k, v in self.query.items())
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        if body is None:
            self.body_binary = b""
        elif isinstance(body, (dict, list)):
            self.body_binary = json.dumps(body).encode("utf-8")
            self.headers.setdefault("content-type", "application/json")
        elif isinstance(body, str):
            self.body_binary = body.encode("utf-8")
        elif isinstance(body, bytes):
            self.body_binary = body
        else:
            self.body_binary = str(body).encode("utf-8")

    @property
    def body_text(self) -> str:
        return self.body_binary.decode("utf-8")

    @property
    def body_json(self):
        return json.loads(self.body_text)

    @property
    def body(self):
        ct = self.headers.get("content-type", "text/plain").lower()
        if ct.startswith("application/json"):
            if len(self.body_binary) > 0:
                return self.body_json
            return {}
        return self.body_text


class FakeResponse:
    def binary(self, body: bytes, statusCode: int = 200, headers: dict | None = None):
        return {"body": body, "statusCode": statusCode, "headers": dict(headers or {})}

    def text(self, body: str, statusCode: int = 200, headers: dict | None = None):
        return self.binary(body.encode("utf-8"), statusCode, headers)

    def json(self, obj, statusCode: int = 200, headers: dict | None = None):
        headers = dict(headers or {})
        headers["content-type"] = "application/json"
        return self.text(json.dumps(obj, separators=(",", ":")), statusCode, headers)

    def empty(self):
        return self.text("", 204, {})


class FakeContext:
    def __init__(self, req: FakeRequest):
        self.req = req
        self.res = FakeResponse()
        self.logs: list[str] = []
        self.errors: list[str] = []

    def log(self, *messages):
        self.logs.append(" ".join(str(m) for m in messages))

    def error(self, *messages):
        self.errors.append(" ".join(str(m) for m in messages))


def decode_body(result: dict) -> Any:
    raw = result["body"]
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = str(raw)
    if not text:
        return None
    return json.loads(text)
