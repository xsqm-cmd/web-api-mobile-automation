"""Web 自动化示例：SauceDemo 登录（Page Object 驱动）。

覆盖点：正向登录、锁定用户、错误密码、空输入、登录后跳转、加购。
面试点：用例里没有 sleep，全部依赖 Playwright 自动等待；失败自动截图+trace。
"""
from __future__ import annotations

import pytest


def test_login_success(web, users):
    from pages.login_page import LoginPage, InventoryPage
    u = users["standard_user"]
    page = LoginPage(web).open_login()
    page.login(u["username"], u["password"])
    assert page.is_logged_in(), "登录后未跳转到库存页"
    inv = InventoryPage(web)
    assert inv.item_count() > 0, "库存页商品数为 0"


def test_login_locked_user(web, users):
    from pages.login_page import LoginPage
    u = users["locked_out_user"]
    page = LoginPage(web).open_login()
    page.login(u["username"], u["password"])
    err = page.error_message()
    assert "locked out" in err.lower(), f"锁定用户提示异常: {err}"


def test_login_invalid_credentials(web, users):
    from pages.login_page import LoginPage
    u = users["invalid_user"]
    page = LoginPage(web).open_login()
    page.login(u["username"], u["password"])
    err = page.error_message()
    assert len(err) > 0, "错误密码未给出提示"


def test_login_empty_credentials(web):
    from pages.login_page import LoginPage
    page = LoginPage(web).open_login()
    page.login("", "")
    err = page.error_message()
    assert "username" in err.lower(), f"空输入提示异常: {err}"


def test_add_to_cart(web, users):
    """端到端业务流：登录 → 加购 → 购物车角标变 1。"""
    from pages.login_page import LoginPage, InventoryPage
    u = users["standard_user"]
    LoginPage(web).open_login().login(u["username"], u["password"])
    inv = InventoryPage(web)
    assert inv.is_logged_in() if hasattr(inv, "is_logged_in") else web.wait_for(InventoryPage.ITEM)
    inv.add_backpack()
    assert inv.cart_count() == "1", f"购物车角标异常: {inv.cart_count()}"
