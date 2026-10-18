"""统一报告：pytest-html 外观 + 自定义摘要 + 三端指标汇总。"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

_META: Dict[str, Any] = {"started": time.time(), "env": "", "cases": {}}


def set_env(env: str) -> None:
    _META["env"] = env


def record(name: str, value: Any) -> None:
    _META["cases"][name] = value


def write_summary(outdir: str = "reports", extra: Dict[str, Any] | None = None) -> str:
    os.makedirs(outdir, exist_ok=True)
    data = {
        "env": _META["env"],
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_META["started"])),
        "duration_s": round(time.time() - _META["started"], 2),
        "cases": _META["cases"],
    }
    if extra:
        data.update(extra)
    p = os.path.join(outdir, "summary.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


# ---- pytest-html 钩子：让默认报告也能带上环境信息 ----
def pytest_configure(config):
    config._metadata = config._metadata or {}
    config._metadata["测试环境"] = _META.get("env") or os.getenv("TEST_ENV", "dev")
    config._metadata["Web Base"] = os.getenv("WEB_BASE_URL", "https://www.saucedemo.com")
    config._metadata["API Base"] = os.getenv("API_BASE_URL", "https://jsonplaceholder.typicode.com")


def pytest_html_report_title(report):
    report.title = "Web / API / Mobile 自动化测试报告"
