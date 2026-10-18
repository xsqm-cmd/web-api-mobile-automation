"""内置 Mock 服务：让脚手架脱离外网也能 100% 跑通。

工程价值（面试可讲）：
  - 接口用例不该依赖不可控的第三方 API，否则 CI 会因为对方抖动而假红
  - Mock 用标准库实现，零依赖，pytest fixture 起在随机端口，用完即停
  - 真实服务只做一层 base_url 切换，用例代码完全不动
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs


POSTS = [
    {"userId": 1, "id": i, "title": f"post-{i}", "body": f"body-{i}"} for i in range(1, 11)
]


class _Handler(BaseHTTPRequestHandler):
    posts = POSTS

    def log_message(self, *a):      # 静音，避免污染 pytest 输出
        pass

    def _send(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _path(self) -> str:
        return urlparse(self.path).path

    def do_GET(self):
        p = self._path()
        if p == "/posts":
            q = parse_qs(urlparse(self.path).query)
            if "userId" in q:
                uid = int(q["userId"][0])
                return self._send(200, [x for x in self.posts if x["userId"] == uid])
            return self._send(200, self.posts)
        if p.startswith("/posts/"):
            pid = int(p.rsplit("/", 1)[-1])
            hit = next((x for x in self.posts if x["id"] == pid), None)
            return self._send(200, hit) if hit else self._send(404, {"error": "not found"})
        if p == "/health":
            return self._send(200, {"status": "ok"})
        if p == "/slow":
            import time
            time.sleep(1.0)
            return self._send(200, {"slow": True})
        if p == "/error":
            return self._send(500, {"error": "boom"})
        return self._send(404, {"error": "no route"})

    def _read_body(self) -> Dict[str, Any]:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_POST(self):
        if self._path() == "/posts":
            d = self._read_body()
            new = {"userId": d.get("userId", 1), "id": len(self.posts) + 1,
                   "title": d.get("title", ""), "body": d.get("body", "")}
            self.posts.append(new)
            return self._send(201, new)
        return self._send(404, {"error": "no route"})

    def do_PUT(self):
        p = self._path()
        if p.startswith("/posts/"):
            pid = int(p.rsplit("/", 1)[-1])
            d = self._read_body()
            hit = next((x for x in self.posts if x["id"] == pid), None)
            if not hit:
                return self._send(404, {"error": "not found"})
            hit.update({k: v for k, v in d.items() if k != "id"})
            return self._send(200, hit)
        return self._send(404, {"error": "no route"})

    def do_PATCH(self):
        p = self._path()
        if p.startswith("/posts/"):
            pid = int(p.rsplit("/", 1)[-1])
            d = self._read_body()
            hit = next((x for x in self.posts if x["id"] == pid), None)
            if not hit:
                return self._send(404, {"error": "not found"})
            hit.update(d)
            return self._send(200, hit)
        return self._send(404, {"error": "no route"})

    def do_DELETE(self):
        p = self._path()
        if p.startswith("/posts/"):
            return self._send(200, {"deleted": True})
        return self._send(404, {"error": "no route"})


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MockServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self._srv: _ThreadingHTTPServer | None = None
        self._th: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> str:
        self._srv = _ThreadingHTTPServer((self.host, self.port), _Handler)
        self.port = self._srv.server_address[1]
        self._th = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._th.start()
        return self.base_url

    def stop(self) -> None:
        try:
            if self._srv:
                self._srv.shutdown()
                self._srv.server_close()
        except Exception:
            pass


def start_mock() -> MockServer:
    m = MockServer()
    m.start()
    return m


if __name__ == "__main__":
    m = start_mock()
    print("mock server at", m.base_url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        m.stop()
