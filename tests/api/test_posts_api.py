"""接口自动化示例。

设计原则：
  - 默认打**本地 mock**（`api_local` fixture），保证 CI 稳定、零外网依赖；
  - 打真实外网 API 的用例单独打 `external` 标记，用 `-m external` 才跑，
    避免第三方抖动让流水线假红。

覆盖点：CRUD 闭环、契约校验、异常路径、性能基线、重试退避、错误封装。
"""
from __future__ import annotations

import pytest

from core.api_client import ApiClient, ApiError

pytestmark = pytest.mark.api


# ---------------- 核心用例（打本地 mock，稳定可重复）----------------
def test_get_posts_list(api_local: ApiClient):
    r = api_local.get("/posts")
    api_local.assert_status(r, 200)
    data = api_local.json(r)
    assert isinstance(data, list) and len(data) > 0
    api_local.assert_json_keys(data[0], ["userId", "id", "title", "body"])


def test_get_post_by_id(api_local: ApiClient):
    r = api_local.get("/posts/1")
    api_local.assert_status(r, 200)
    d = api_local.json(r)
    assert d["id"] == 1
    api_local.assert_json_keys(d, ["userId", "id", "title", "body"])


def test_get_post_not_found(api_local: ApiClient):
    r = api_local.get("/posts/999999")
    api_local.assert_status(r, 404)


def test_create_post(api_local: ApiClient):
    payload = {"title": "aitp test", "body": "hello", "userId": 1}
    r = api_local.post("/posts", json=payload)
    api_local.assert_status(r, (200, 201))
    d = api_local.json(r)
    assert d["title"] == payload["title"]
    assert "id" in d


def test_update_post_put(api_local: ApiClient):
    r = api_local.put("/posts/2", json={"title": "updated", "body": "x", "userId": 1})
    api_local.assert_status(r, 200)
    assert api_local.json(r)["title"] == "updated"


def test_patch_post(api_local: ApiClient):
    r = api_local.patch("/posts/3", json={"title": "patched"})
    api_local.assert_status(r, 200)
    assert api_local.json(r)["title"] == "patched"


def test_delete_post(api_local: ApiClient):
    r = api_local.delete("/posts/4")
    api_local.assert_status(r, (200, 204))


def test_contract_post_schema(api_local: ApiClient):
    """契约校验：字段类型不许漂移（接口自动化最容易被忽略的一层）。"""
    r = api_local.get("/posts/1")
    api_local.assert_status(r, 200)
    d = api_local.json(r)
    assert isinstance(d["userId"], int), "userId 应为 int"
    assert isinstance(d["id"], int), "id 应为 int"
    assert isinstance(d["title"], str), "title 应为 str"
    assert isinstance(d["body"], str), "body 应为 str"


@pytest.mark.perf
def test_response_time_baseline(api_local: ApiClient):
    """性能基线：本地 P95 必须低于 500ms，防止接口静默劣化。"""
    for _ in range(10):
        api_local.get("/posts")
    s = api_local.summary()
    assert s["count"] >= 10
    api_local.assert_lt(s["p95_ms"], 500, "接口 P95 耗时")


def test_retry_on_5xx(api_local: ApiClient):
    """重试与退避：5xx 应触发重试后仍返回响应，不抛异常。"""
    r = api_local.get("/error")
    assert r.status_code == 500


def test_query_filter(api_local: ApiClient):
    r = api_local.get("/posts", params={"userId": 1})
    api_local.assert_status(r, 200)
    data = api_local.json(r)
    assert all(x["userId"] == 1 for x in data)


def test_api_error_is_wrapped():
    """异常封装：不可达地址应抛 ApiError 而不是裸 ConnectionError。"""
    bad = ApiClient(base_url="http://127.0.0.1:1", retries=0, timeout=1.0)
    with pytest.raises(ApiError):
        bad.get("/posts")


def test_metrics_recorded(api_local: ApiClient):
    """可观测性：每次请求都记录 method/url/status/耗时，供报告统计。"""
    api_local.get("/health")
    s = api_local.summary()
    assert s["count"] >= 1
    assert "p95_ms" in s and "max_ms" in s


# ---------------- 外网用例（默认不跑，需 -m external）----------------
@pytest.mark.external
def test_external_public_api(api: ApiClient):
    """真实外网 API 冒烟：验证客户端封装对真实服务同样有效。"""
    r = api.get("/posts/1")
    api.assert_status(r, 200)
    d = api.json(r)
    assert d["id"] == 1
