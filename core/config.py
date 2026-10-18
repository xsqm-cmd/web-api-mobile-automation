"""统一配置：一套配置管三端（Web / API / Mobile）。

优先级：环境变量 > config/env.yaml > 默认值
面试点：把"环境切换"从代码里剥离，是测试框架工程化的第一步。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Any

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class WebConfig:
    base_url: str = "https://www.saucedemo.com"
    browser: str = "chromium"        # chromium | firefox | webkit
    headless: bool = True
    timeout_ms: int = 15000
    slow_mo_ms: int = 0
    trace: bool = True               # Playwright trace：失败自动留证
    screenshot_on_fail: bool = True


@dataclass
class ApiConfig:
    base_url: str = "https://jsonplaceholder.typicode.com"
    timeout_s: float = 10.0
    verify_ssl: bool = True
    retries: int = 2
    retry_backoff: float = 0.5


@dataclass
class MobileConfig:
    platform: str = "Android"        # Android | iOS
    appium_server: str = "http://127.0.0.1:4723"
    app_package: str = "com.swaglabsmobileapp"
    app_activity: str = "com.swaglabsmobileapp.MainActivity"
    implicit_wait_s: int = 10
    enabled: bool = False            # 无真机/模拟器时自动跳过移动端用例


@dataclass
class ReportConfig:
    dir: str = "reports"
    allure: bool = True
    html: bool = True


@dataclass
class Config:
    env: str = "dev"
    web: WebConfig = field(default_factory=WebConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    mobile: MobileConfig = field(default_factory=MobileConfig)
    report: ReportConfig = field(default_factory=ReportConfig)


_DEFAULTS: Dict[str, Any] = {
    "dev": {
        "web": {"base_url": "https://www.saucedemo.com", "headless": True},
        "api": {"base_url": "https://jsonplaceholder.typicode.com"},
    },
    "test": {
        "web": {"base_url": "https://www.saucedemo.com", "headless": True},
        "api": {"base_url": "https://jsonplaceholder.typicode.com"},
    },
    "prod": {
        "web": {"base_url": "https://www.saucedemo.com", "headless": True},
        "api": {"base_url": "https://jsonplaceholder.typicode.com"},
    },
}


def _deep_update(base: dict, override: dict) -> dict:
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
    return base


def load_config(env: str | None = None, path: str = "config/env.yaml") -> Config:
    env = env or os.getenv("TEST_ENV", "dev")
    data: Dict[str, Any] = {k: (v.copy() if isinstance(v, dict) else v)
                            for k, v in _DEFAULTS.get(env, _DEFAULTS["dev"]).items()}
    if yaml and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
        if env in y:
            _deep_update(data, y[env])

    # 环境变量覆盖
    if os.getenv("WEB_BASE_URL"):
        data.setdefault("web", {})["base_url"] = os.environ["WEB_BASE_URL"]
    if os.getenv("API_BASE_URL"):
        data.setdefault("api", {})["base_url"] = os.environ["API_BASE_URL"]
    if os.getenv("HEADLESS"):
        data.setdefault("web", {})["headless"] = os.environ["HEADLESS"].lower() in ("1", "true", "yes")
    if os.getenv("APPIUM_SERVER"):
        data.setdefault("mobile", {})["appium_server"] = os.environ["APPIUM_SERVER"]
    if os.getenv("MOBILE_ENABLED"):
        data.setdefault("mobile", {})["enabled"] = os.environ["MOBILE_ENABLED"].lower() in ("1", "true", "yes")

    return Config(
        env=env,
        web=WebConfig(**data.get("web", {})),
        api=ApiConfig(**data.get("api", {})),
        mobile=MobileConfig(**data.get("mobile", {})),
        report=ReportConfig(**data.get("report", {})),
    )


CFG = load_config()
