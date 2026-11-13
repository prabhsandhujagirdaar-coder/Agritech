"""TestClient compatibility shim for running tests without external httpx/httpx2 dependency."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

# Use lightweight in-process ASGI TestClient to bypass Starlette 1.7+ anyio/httpx2 deadlocks on Windows/Python 3.13
class ASGIResponse:
    def __init__(self, status_code: int, headers: list, body: bytes):
        self.status_code = status_code
        self.headers = {
            (k.decode("latin-1") if isinstance(k, bytes) else k): (
                v.decode("latin-1") if isinstance(v, bytes) else v
            )
            for k, v in headers
        }
        self.content = body

    def json(self) -> Any:
        return json.loads(self.content.decode("utf-8"))

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

class TestClient:
    def __init__(self, app: Any):
        self.app = app

    def __enter__(self) -> "TestClient":
        if not hasattr(self.app.state, "cnn_service") or self.app.state.cnn_service is None:
            from app.services.cnn_service import CNNService
            self.app.state.cnn_service = CNNService()
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> ASGIResponse:
        return self._request("GET", path, headers=headers)

    def post(
        self,
        path: str,
        json: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ASGIResponse:
        body = b""
        hdrs = dict(headers or {})
        if json is not None:
            body = _safe_json_dumps(json)
            hdrs["content-type"] = "application/json"
        elif files is not None:
            boundary = "----WebKitFormBoundaryTestClient2026"
            hdrs["content-type"] = f"multipart/form-data; boundary={boundary}"
            parts = []
            for field, ftuple in files.items():
                if isinstance(ftuple, tuple):
                    fname = ftuple[0]
                    fbytes = ftuple[1]
                    ctype = ftuple[2] if len(ftuple) > 2 else "application/octet-stream"
                else:
                    fname = "file"
                    fbytes = ftuple
                    ctype = "application/octet-stream"
                parts.append(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{fname}\"\r\nContent-Type: {ctype}\r\n\r\n".encode("utf-8")
                    + fbytes
                    + b"\r\n"
                )
            parts.append(f"--{boundary}--\r\n".encode("utf-8"))
            body = b"".join(parts)
        return self._request("POST", path, headers=hdrs, body=body)

    def put(
        self,
        path: str,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ASGIResponse:
        body = b""
        hdrs = dict(headers or {})
        if json is not None:
            body = _safe_json_dumps(json)
            hdrs["content-type"] = "application/json"
        return self._request("PUT", path, headers=hdrs, body=body)

    def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> ASGIResponse:
        return self._request("DELETE", path, headers=headers)

    def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: bytes = b"",
    ) -> ASGIResponse:
        status_code = [200]
        resp_headers: list = []
        resp_body: list = []

        if "?" in path:
            raw_path_str, query_str = path.split("?", 1)
        else:
            raw_path_str, query_str = path, ""

        hdrs = dict(headers or {})
        if body and "content-length" not in [k.lower() for k in hdrs]:
            hdrs["content-length"] = str(len(body))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "path": raw_path_str,
            "raw_path": raw_path_str.encode("latin-1"),
            "query_string": query_str.encode("latin-1"),
            "headers": [
                (k.lower().encode("latin-1"), str(v).encode("latin-1"))
                for k, v in hdrs.items()
            ],
        }

        sent = False

        async def receive() -> Dict[str, Any]:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: Dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
                resp_headers.extend(message.get("headers", []))
            elif message["type"] == "http.response.body":
                resp_body.append(message.get("body", b""))

        asyncio.run(self.app(scope, receive, send))
        return ASGIResponse(status_code[0], resp_headers, b"".join(resp_body))


def _safe_json_dumps(data: Any) -> bytes:
    return json.dumps(data).encode("utf-8")
