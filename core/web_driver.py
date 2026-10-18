"""Playwright 驱动封装：Web 自动化的地基。

面试点：
  - 显式等待优先（Playwright auto-waiting），杜绝 sleep
  - trace + screenshot + video 自动留证，失败可回放
  - Page Object 基类，把定位器与业务动作收敛在 pages/
"""
from __future__ import annotations

import os
from typing import Any

try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False
    sync_playwright = None
    Browser = Page = BrowserContext = Any


class WebSession:
    """一个测试会话 = 一个 browser + 一个 context + 一个 page。"""

    def __init__(self, base_url: str, browser: str = "chromium", headless: bool = True,
                 timeout_ms: int = 15000, slow_mo_ms: int = 0, trace: bool = True,
                 screenshot_on_fail: bool = True, artifacts_dir: str = "reports/artifacts"):
        self.base_url = base_url
        self.browser_name = browser
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.slow_mo_ms = slow_mo_ms
        self.trace = trace
        self.screenshot_on_fail = screenshot_on_fail
        self.artifacts_dir = artifacts_dir
        self._pw = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None

    def __enter__(self) -> "WebSession":
        if not PLAYWRIGHT_OK:
            raise RuntimeError("未安装 playwright：pip install playwright && playwright install")
        os.makedirs(self.artifacts_dir, exist_ok=True)
        self._pw = sync_playwright().start()
        factory = getattr(self._pw, self.browser_name)
        self.browser = factory.launch(headless=self.headless, slow_mo=self.slow_mo_ms)
        self.context = self.browser.new_context(
            base_url=self.base_url,
            viewport={"width": 1440, "height": 900},
            record_video_dir=self.artifacts_dir if not self.headless else None,
        )
        self.context.set_default_timeout(self.timeout_ms)
        if self.trace:
            self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.trace and self.context:
                self.context.tracing.stop(path=os.path.join(self.artifacts_dir, "trace.zip"))
            if exc_type is not None and self.screenshot_on_fail and self.page:
                self.page.screenshot(path=os.path.join(self.artifacts_dir, "failure.png"),
                                     full_page=True)
        finally:
            for close in (self.context, self.browser):
                try:
                    close.close() if close else None
                except Exception:
                    pass
            try:
                self._pw.stop() if self._pw else None
            except Exception:
                pass

    # ---------- 常用动作（封装显式等待）----------
    def goto(self, path: str = "/") -> Any:
        return self.page.goto(path if path.startswith("http") else path)

    def fill(self, selector: str, value: str) -> None:
        self.page.fill(selector, value)

    def click(self, selector: str) -> None:
        self.page.click(selector)

    def text(self, selector: str) -> str:
        return self.page.inner_text(selector)

    def wait_for(self, selector: str, timeout: int | None = None) -> None:
        self.page.wait_for_selector(selector, timeout=timeout or self.timeout_ms)

    def expect_text(self, selector: str, text: str) -> None:
        from playwright.sync_api import expect
        expect(self.page.locator(selector)).to_contain_text(text)


class BasePage:
    """Page Object 基类。所有 pages/ 下的类继承它。"""

    def __init__(self, session: WebSession):
        self.s = session
        self.page = session.page

    def open(self, path: str = "/") -> None:
        self.s.goto(path)
