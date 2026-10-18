.PHONY: install install-min api web mobile all external

install:
	pip install -r requirements.txt
	playwright install chromium

install-min:            # 只跑接口 + 自测的最小安装
	pip install -r requirements-min.txt

api:                    # 接口回归（本地 mock，最快最稳）
	pytest tests/api tests/test_framework_selftest.py -q

web:                    # Web 回归（需 playwright）
	pytest tests/web -q

mobile:                 # 移动端冒烟（需 Appium）
	MOBILE_ENABLED=1 pytest tests/mobile -q

external:               # 外网真实 API 冒烟（默认不跑）
	pytest tests/api -m external -q

all: api web
