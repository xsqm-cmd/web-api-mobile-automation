# Web / API / Mobile 三端自动化测试脚手架

一套 pytest 驱动的三端统一自动化脚手架：**Web（Playwright）+ 接口（Requests）+ 移动端（Appium）**，
内置 Mock 服务、配置分层、契约校验、性能基线与失败留证。

> 面试定位：测试开发自研项目。覆盖 JD 高频关键词
> **pytest / Playwright / Appium / Requests / Page Object / CI-CD / 接口契约 / 性能基线**。

---

## 1. 解决什么问题

| 痛点 | 脚手架解法 |
|---|---|
| Web、接口、移动端各写一套脚本，重复维护 | 统一组织层：同一套 pytest + fixture + 配置 + 报告 |
| 切换测试环境要改代码 | 配置三级覆盖：环境变量 > YAML > 默认值，用例代码零改动 |
| 接口用例依赖第三方公开 API，CI 频繁假红 | 标准库内置 Mock 服务 + 随机端口，默认打本地零外网 |
| 偶发失败只能重跑碰运气 | 会话级 trace + 录屏 + 失败自动截图 |
| 没装 Playwright / 没起 Appium 就报 error | 环境缺失自动 skip 并输出原因，与真实失败区分 |
| 接口劣化（字段漂移、延迟变慢）没人发现 | 字段契约校验 + P95 性能基线 |
| 靠重试掩盖失败 | 仅连接层异常与 5xx 重试、4xx 不重试，指数退避，metrics 全程可见 |

---

## 2. 目录结构

```
web-api-mobile-automation/
├── conftest.py               # 全局 fixture：mock / api / web / mobile / users
├── pytest.ini                # 用例标记：web / api / mobile / perf / external / smoke
├── core/
│   ├── config.py             # 配置加载：环境变量 > YAML > 默认值
│   ├── api_client.py         # Requests 封装：重试退避 + 契约校验 + metrics
│   ├── web_driver.py         # Playwright 会话：trace + 录屏 + 失败留证
│   ├── mobile_driver.py      # Appium 会话封装
│   └── report.py             # pytest-html 报告定制 + summary 汇总
├── pages/login_page.py       # Page Object：定位器集中，页面改版只改一处
├── mock/server.py            # 标准库实现的 Mock 服务（随机端口）
├── config/env.yaml           # dev / test / prod 三套环境
├── data/users.json           # 测试数据
└── tests/
    ├── api/                  # 接口用例（默认打本地 Mock）
    ├── web/                  # Web 用例（Playwright）
    ├── mobile/               # 移动端用例（无环境自动跳过）
    └── test_framework_selftest.py   # 框架自测
```

---

## 3. 快速开始

```bash
pip install -r requirements.txt

# 默认全量（接口走本地 Mock，零外网依赖）
pytest

# 指定环境
pytest --env test

# 只跑接口 / Web / 移动端
pytest -m api
pytest -m web
pytest -m mobile

# 打真实外网的冒烟用例（默认不跑，手动或发版前触发）
pytest -m external
```

Web 端首次运行需要安装浏览器：

```bash
pip install playwright && playwright install chromium
```

---

## 4. 关键设计

### 4.1 内置 Mock：CI 稳定性的根因治理

接口回归默认打本地 Mock（标准库实现，起在随机端口），
真实服务通过切换 base_url 接入，**用例代码一行不动**。
实测对比：依赖外网时 124 秒且偶发失败 → 本地 Mock 2.71 秒稳定全绿
（两者被测对象不同，前者为第三方公开 API、后者为本地 Mock，不可直接横向比较）。

### 4.2 用例分层：稳定性与真实观测兼得

打真实服务的冒烟用例单独打 `external` 标记，不进默认流水线，
定时或发版前手动触发，既保住 CI 稳定性，又不放弃对真实依赖的观测。

### 4.3 配置三级覆盖

环境变量 > YAML > 默认值。CI 改配置只需设环境变量，不需要改任何用例代码。

### 4.4 环境缺失容错

未装 Playwright 或未起 Appium 时，相应用例自动 skip 并输出明确原因，
使流水线结果与真实缺陷区分开，不因环境不全误判失败。

### 4.5 接口校验深度

在状态码之外增加字段契约校验（类型漂移可被发现）与 P95 性能基线
（防止静默劣化），并覆盖不存在资源、参数非法等异常路径。

### 4.6 重试与退避

仅对连接层异常与 5xx 重试，4xx 业务错误不重试，采用指数退避；
每次请求记录耗时与状态码进 metrics，使「靠重试掩盖的失败」在趋势数据中仍可见。

### 4.7 失败留证

会话级开启操作轨迹与录屏，失败钩子里自动截图，Web 用例偶发失败可事后还原。
所有留证动作绑定失败条件以控制开销。

### 4.8 工程化与自测

Page Object 模式收效定位器使页面改版只改一处；为配置加载、断言辅助函数与报告汇总
编写自测用例，保证脚手架演进不破坏既有能力；GitHub Actions 按端拆分并行，Docker 一键执行。

---

## 5. 实测结果

```
21 passed, 8 skipped in 2.71s     # 全本地 Mock，零外网依赖
```

`8 skipped` 为 Web / 移动端环境未安装时的自动跳过（设计行为，非失败）。
GitHub Actions 按端拆分并行执行，Docker 一键复现。

---

## 6. 简历话术

> **自研 Web / API / Mobile 三端自动化测试脚手架**
> 基于 pytest + Playwright + Appium + Requests，统一 Web、接口、移动端三端自动化。
> 用标准库实现内置 Mock 服务，接口回归默认打本地、零外网依赖，
> 实测由依赖外网时的 124 秒且偶发失败变为 2.71 秒稳定全绿；
> 支持环境变量 > YAML > 默认值三级配置覆盖，切换环境不改用例代码；
> 增加字段契约校验与 P95 性能基线；会话级 trace + 录屏 + 失败自动截图实现失败留证；
> 环境缺失自动 skip，使流水线结果与真实缺陷区分开。