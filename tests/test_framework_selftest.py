"""框架自测：不依赖网络与浏览器，验证脚手架自身组件。

面试点：框架本身被测试——配置加载、断言 helper、重试/退避、报告汇总。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_config, Config
from core.api_client import ApiClient
from core import report as rep


def test_config_default():
    c: Config = load_config("dev")
    assert c.env == "dev"
    assert c.web.base_url.startswith("http")
    assert c.api.base_url.startswith("http")


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://example.test")
    monkeypatch.setenv("HEADLESS", "false")
    c = load_config("dev")
    assert c.api.base_url == "http://example.test"
    assert c.web.headless is False


def test_config_mobile_disabled_by_default():
    c = load_config("dev")
    assert c.mobile.enabled is False


def test_assert_status_helper():
    class R:
        status_code = 404
        text = "not found"
        def json(self): return {}
    try:
        ApiClient.assert_status(R(), 200)
        assert False, "应当断言失败"
    except AssertionError as e:
        assert "状态码断言失败" in str(e)


def test_assert_json_keys():
    assert ApiClient.assert_json_keys({"a": 1, "b": 2}, ["a", "b"]) == {"a": 1, "b": 2}
    try:
        ApiClient.assert_json_keys({"a": 1}, ["a", "z"])
        assert False, "应当断言失败"
    except AssertionError as e:
        assert "缺少字段" in str(e)


def test_summary_empty():
    c = ApiClient(base_url="http://x")
    assert c.summary() == {"count": 0}


def test_report_summary_written(tmp_path):
    rep.set_env("selftest")
    rep.record("demo", 1)
    p = rep.write_summary(str(tmp_path))
    assert os.path.exists(p)
    import json
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    assert d["env"] == "selftest"
    assert d["cases"]["demo"] == 1
