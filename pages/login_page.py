"""Page Object 示例：SauceDemo 登录页。

面试点：定位器集中管理 + 业务动作语义化 + 断言前先等待，用例层零 sleep。
"""
from __future__ import annotations

from core.web_driver import BasePage


class LoginPage(BasePage):
    URL = "/"

    # ---- 定位器（集中管理，改一处即可）----
    USERNAME = "[data-test='username']"
    PASSWORD = "[data-test='password']"
    LOGIN_BTN = "[data-test='login-button']"
    ERROR = "[data-test='error']"
    INVENTORY = "[data-test='inventory-container']"

    def open_login(self):
        self.open(self.URL)
        self.s.wait_for(self.LOGIN_BTN)
        return self

    def login(self, username: str, password: str) -> None:
        self.s.fill(self.USERNAME, username)
        self.s.fill(self.PASSWORD, password)
        self.s.click(self.LOGIN_BTN)

    def error_message(self) -> str:
        self.s.wait_for(self.ERROR)
        return self.s.text(self.ERROR)

    def is_logged_in(self) -> bool:
        try:
            self.s.wait_for(self.INVENTORY, timeout=5000)
            return True
        except Exception:
            return False


class InventoryPage(BasePage):
    URL = "/inventory.html"

    CART_BADGE = "[data-test='shopping-cart-badge']"
    CART_LINK = "[data-test='shopping-cart-link']"
    ITEM = "[data-test='inventory-item']"
    ADD_BACKPACK = "[data-test='add-to-cart-sauce-labs-backpack']"

    def item_count(self) -> int:
        return self.page.locator(self.ITEM).count()

    def add_backpack(self) -> None:
        self.s.click(self.ADD_BACKPACK)

    def cart_count(self) -> str:
        return self.s.text(self.CART_BADGE)
