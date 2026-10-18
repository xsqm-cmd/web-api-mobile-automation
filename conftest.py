"""pytest 全局夹具：三端共享。

面试点：
  - fixture 分层（session / function），避免每个用例重复建链
  - 移动端无环境自动 skip，CI 不因环境缺失变红
  - 失败自动截图 / trace，报告里能直接看现场
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import load_config, CFG
from core.api_client import ApiClient
from core import report as rep


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default=None, help="运行环境: dev/test/prod")


def pytest_configure(config):
    env = config.getoption("--env") or os.getenv("TEST_ENV", "dev")
    rep.set_env(env)
    try:
        rep.pytest_configure(config)
    except Exception:
        pass


def pytest_html_report_title(report):
    try:
        rep.pytest_html_report_title(report)
    except Exception:
        pass


@pytest.fixture(scope="session")
def cfg() -> "CFG.__class__":
    return load_config(os.getenv("TEST_ENV", "dev"))


# ---------------- API ----------------
# ---------------- Mock（脱离外网跑通的关键）----------------
@pytest.fixture(scope="session")
def mock_server():
    """起一个本地 mock 服务：接口用例默认打本地，CI 不因外网抖动假红。"""
    from mock.server import start_mock
    m = start_mock()
    yield m
    m.stop()


@pytest.fixture(scope="session")
def api(cfg) -> ApiClient:
    return ApiClient(base_url=cfg.api.base_url, timeout=cfg.api.timeout_s,
                     retries=cfg.api.retries, backoff=cfg.api.retry_backoff)


# ---------------- Web ----------------
@pytest.fixture(scope="function")
def web(cfg):
    """每个用例一个独立 session，失败自动留 trace + 截图。"""
    from core.web_driver import WebSession
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright 未安装，跳过 Web 用例（pip install playwright && playwright install）")
    s = WebSession(base_url=cfg.web.base_url, browser=cfg.web.browser,
                   headless=cfg.web.headless, timeout_ms=cfg.web.timeout_ms,
                   slow_mo_ms=cfg.web.slow_mo_ms, trace=cfg.web.trace,
                   artifacts_dir=os.path.join(cfg.report.dir, "artifacts"))
    try:
        ctx = s.__enter__()
    except Exception as e:
        # 包已装但浏览器二进制缺失（playwright install 未执行）时同样跳过，
        # 避免把环境问题报成 error，污染流水线判定
        pytest.skip(f"Web 环境不可用，跳过 Web 用例：{type(e).__name__}: {str(e)[:200]}")
    try:
        yield ctx
    finally:
        s.__exit__(None, None, None)


# ---------------- Mobile ----------------
@pytest.fixture(scope="function")
def mobile(cfg):
    from core.mobile_driver import MobileSession
    if not cfg.mobile.enabled:
        pytest.skip("移动端未启用（设置 MOBILE_ENABLED=1 且启动 Appium 后生效）")
    m = MobileSession(server=cfg.mobile.appium_server, platform=cfg.mobile.platform,
                      app_package=cfg.mobile.app_package, app_activity=cfg.mobile.app_activity)
    drv = m.start()
    yield drv
    m.stop()


# ---------------- 数据 ----------------
@pytest.fixture(scope="session")
def api_local(mock_server) -> ApiClient:
    """打本地 mock 的接口客户端（默认推荐）。"""
    return ApiClient(base_url=mock_server.base_url, timeout=5.0, retries=1, backoff=0.1)


@pytest.fixture(scope="session")
def users() -> dict:
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "users.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()
    if result.when == "call" and result.failed:
        # 失败时把 Web 现场留证到 artifacts
        try:
            sess = item.funcargs.get("web")
            if sess and sess.page:
                d = os.path.join(CFG.report.dir, "artifacts")
                os.makedirs(d, exist_ok=True)
                sess.page.screenshot(path=os.path.join(d, f"{item.name}.png"), full_page=True)
        except Exception:
            pass


def pytest_sessionfinish(session, exitstatus):
    try:
        rep.write_summary(CFG.report.dir, {"pytest_exitstatus": int(exitstatus)})
    except Exception:
        pass


