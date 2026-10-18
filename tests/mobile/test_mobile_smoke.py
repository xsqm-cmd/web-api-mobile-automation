"""移动端冒烟示例：无环境自动 skip（CI 不会因为缺真机变红）。

启用方式：
    MOBILE_ENABLED=1 APPIUM_SERVER=http://127.0.0.1:4723 pytest tests/mobile -v
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.mobile


def test_app_launched(mobile):
    """App 启动后应能拿到当前 package。"""
    pkg = mobile.current_package
    assert pkg, "未获取到当前包名"
    assert isinstance(pkg, str)


def test_app_screenshot(mobile, tmp_path):
    p = str(tmp_path / "mobile.png")
    mobile.save_screenshot(p)
    import os
    assert os.path.exists(p) and os.path.getsize(p) > 0


def test_login_page_elements(mobile):
    """登录页关键元素存在性（示例定位器，按真实 App 调整）。"""
    els = mobile.find_elements("xpath", "//*[@content-desc='test-Username']")
    assert els is not None
