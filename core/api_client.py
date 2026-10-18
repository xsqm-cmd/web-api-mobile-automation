"""HTTP 客户端封装：接口自动化的地基。

面试点：
  - 统一超时 / 重试 / 指数退避，避免"接口抖动导致用例假失败"
  - 自动记录请求耗时，供性能基线与报告使用
  - 内置断言 helper（status / json schema / 字段），让用例只写业务
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import requests


class ApiError(Exception):
    def __init__(self, msg: str, resp: "requests.Response | None" = None):
        super().__init__(msg)
        self.resp = resp


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0, retries: int = 2,
                 backoff: float = 0.5, verify_ssl: bool = True,
                 default_headers: Optional[Dict[str, str]] = None, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.verify_ssl = verify_ssl
        self.session = session or requests.Session()
        if default_headers:
            self.session.headers.update(default_headers)
        self.metrics: list = []       # 每次请求的耗时记录，供报告统计

    # ---------- 基础请求 ----------
    def request(self, method: str, path: str, **kw) -> requests.Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        last = None
        for attempt in range(self.retries + 1):
            t0 = time.time()
            try:
                resp = self.session.request(method.upper(), url, timeout=self.timeout,
                                            verify=self.verify_ssl, **kw)
            except requests.RequestException as e:
                last = e
                self.metrics.append({"method": method, "url": url, "ms": int((time.time()-t0)*1000),
                                     "status": 0, "error": str(e)})
                if attempt < self.retries:
                    time.sleep(self.backoff * (2 ** attempt))
                    continue
                raise ApiError(f"请求异常: {e}") from e
            ms = int((time.time() - t0) * 1000)
            self.metrics.append({"method": method.upper(), "url": url, "ms": ms,
                                 "status": resp.status_code})
            # 5xx 才重试；4xx 是业务错误，不重试
            if 500 <= resp.status_code < 600 and attempt < self.retries:
                time.sleep(self.backoff * (2 ** attempt))
                continue
            return resp
        if last:
            raise ApiError(f"请求异常: {last}")
        raise ApiError("请求失败")

    def get(self, p, **kw): return self.request("GET", p, **kw)
    def post(self, p, **kw): return self.request("POST", p, **kw)
    def put(self, p, **kw): return self.request("PUT", p, **kw)
    def patch(self, p, **kw): return self.request("PATCH", p, **kw)
    def delete(self, p, **kw): return self.request("DELETE", p, **kw)

    # ---------- 断言 helper ----------
    @staticmethod
    def assert_status(resp: requests.Response, expected: int | tuple = 200) -> requests.Response:
        exp = (expected,) if isinstance(expected, int) else tuple(expected)
        assert resp.status_code in exp, (
            f"状态码断言失败: 期望 {exp}，实际 {resp.status_code}，body={resp.text[:300]}"
        )
        return resp

    @staticmethod
    def assert_json_keys(data: Any, keys: list) -> Any:
        assert isinstance(data, (dict, list)), f"响应不是 JSON 结构: {type(data)}"
        if isinstance(data, dict):
            missing = [k for k in keys if k not in data]
            assert not missing, f"缺少字段: {missing}，实际字段: {list(data.keys())}"
        return data

    @staticmethod
    def assert_lt(actual: float, limit: float, what: str = "值") -> None:
        assert actual < limit, f"{what} 超限: {actual} >= {limit}"

    @staticmethod
    def json(resp: requests.Response) -> Any:
        try:
            return resp.json()
        except Exception as e:
            raise ApiError(f"响应非 JSON: {e}, body={resp.text[:300]}", resp) from e

    # ---------- 报告数据 ----------
    def summary(self) -> Dict[str, Any]:
        if not self.metrics:
            return {"count": 0}
        ms = sorted(m["ms"] for m in self.metrics)
        return {
            "count": len(self.metrics),
            "p50_ms": ms[len(ms)//2],
            "p95_ms": ms[max(0, int(len(ms)*0.95)-1)],
            "max_ms": ms[-1],
            "errors": sum(1 for m in self.metrics if m.get("status", 0) >= 400),
        }
