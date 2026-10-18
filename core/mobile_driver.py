"""Appium 驱动封装：Mobile 自动化的地基。

无真机 / 模拟器时，用例会自动 skip（CI 不会因为环境缺失而红）。
"""
from __future__ import annotations

import os
from typing import Any

try:
    from appium import webdriver as appium_webdriver
    from appium.options.android import UiAutomator2Options
    APPIUM_OK = True
except ImportError:
    APPIUM_OK = False
    appium_webdriver = None
    UiAutomator2Options = Any


class MobileSession:
    def __init__(self, server: str, platform: str = "Android",
                 app_package: str = "", app_activity: str = "",
                 implicit_wait_s: int = 10, no_reset: bool = True):
        self.server = server
        self.platform = platform
        self.app_package = app_package
        self.app_activity = app_activity
        self.implicit_wait_s = implicit_wait_s
        self.no_reset = no_reset
        self.driver: Any = None

    def options(self):
        o = UiAutomator2Options()
        o.platform_name = self.platform
        o.automation_name = "UiAutomator2"
        o.app_package = self.app_package
        o.app_activity = self.app_activity
        o.no_reset = self.no_reset
        o.new_command_timeout = 120
        return o

    def start(self) -> Any:
        if not APPIUM_OK:
            raise RuntimeError("未安装 Appium-Python-Client：pip install Appium-Python-Client")
        self.driver = appium_webdriver.Remote(self.server, options=self.options())
        self.driver.implicitly_wait(self.implicit_wait_s)
        return self.driver

    def stop(self) -> None:
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

    def screenshot(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if self.driver:
            self.driver.save_screenshot(path)
