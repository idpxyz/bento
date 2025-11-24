.PHONY: help fmt lint test test-cov clean build install install-dev publish publish-test release run dev

# Python 解释器（智能检测：优先虚拟环境，支持 python3 或 python）
PYTHON := $(shell \
	if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; \
	elif [ -f .venv/bin/python ]; then echo .venv/bin/python; \
	elif command -v python3 >/dev/null 2>&1; then echo python3; \
	elif command -v python >/dev/null 2>&1; then echo python; \
	else echo "python3"; fi)

PIP := $(shell \
	if [ -f .venv/bin/pip3 ]; then echo .venv/bin/pip3; \
	elif [ -f .venv/bin/pip ]; then echo .venv/bin/pip; \
	elif command -v pip3 >/dev/null 2>&1; then echo pip3; \
	elif command -v pip >/dev/null 2>&1; then echo pip; \
	else echo "pip"; fi)

# Python 版本检测
PYTHON_VERSION := $(shell $(PYTHON) -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "0.0")
PYTHON_VERSION_MAJOR := $(shell echo $(PYTHON_VERSION) | cut -d. -f1)
PYTHON_VERSION_MINOR := $(shell echo $(PYTHON_VERSION) | cut -d. -f2)

# 检查 Python 版本（需要 3.12.x）
.PHONY: check-python
check-python:
	@if [ "$(PYTHON_VERSION_MAJOR)" != "3" ] || [ "$(PYTHON_VERSION_MINOR)" -lt "12" ]; then \
		echo "❌ Python 版本不符合要求"; \
		echo "   需要: Python 3.12.x"; \
		echo "   当前: Python $(PYTHON_VERSION)"; \
		echo ""; \
		echo "请安装 Python 3.12:"; \
		echo "  Ubuntu: sudo apt install python3.12"; \
		echo "  macOS:  brew install python@3.12"; \
		exit 1; \
	fi

# 默认目标
help:
	@echo "Bento Framework - Makefile 命令"
	@echo ""
	@echo "Python: $(PYTHON)"
	@echo "版本:   $(PYTHON_VERSION) (需要 3.12.x)"
	@echo ""
	@echo "开发命令:"
	@echo "  make fmt          - 格式化代码"
	@echo "  make lint         - 代码检查"
	@echo "  make test         - 运行测试"
	@echo "  make test-cov     - 运行测试并生成覆盖率报告"
	@echo "  make dev          - 启动开发服务器"
	@echo ""
	@echo "构建和发布:"
	@echo "  make clean        - 清理构建文件"
	@echo "  make build        - 构建包"
	@echo "  make install      - 安装包（生产）"
	@echo "  make install-dev  - 安装包（开发）"
	@echo "  make publish-test - 发布到 Test PyPI"
	@echo "  make publish      - 发布到 PyPI"
	@echo "  make release      - 完整发布流程"
	@echo ""

# 代码格式化
fmt:
	@echo "🎨 格式化代码..."
	$(PYTHON) -m ruff check --fix src/
	$(PYTHON) -m ruff format src/

# 代码检查
lint:
	@echo "🔍 代码检查..."
	$(PYTHON) -m ruff check src/
	@echo "🔍 类型检查..."
	-$(PYTHON) -m mypy src/bento || echo "⚠️  MyPy 检查有警告（不影响发布）"

# 运行测试
test: check-python
	@echo "🧪 运行测试..."
	$(PYTHON) -m pytest

# 运行测试并生成覆盖率
test-cov: check-python
	@echo "🧪 运行测试（带覆盖率）..."
	$(PYTHON) -m pytest --cov --cov-report=html --cov-report=term-missing
	@echo "📊 覆盖率报告: htmlcov/index.html"

# 清理构建文件
clean:
	@echo "🧹 清理构建文件..."
	rm -rf build/ dist/ *.egg-info
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ 清理完成"

# 构建包
build: check-python clean
	@echo "📦 构建包..."
	$(PYTHON) -m build
	@echo "✅ 构建完成: dist/"

# 安装包（生产）
install: check-python
	@echo "📥 安装 Bento Framework..."
	$(PIP) install -e .

# 安装包（开发）
install-dev: check-python
	@echo "📥 安装 Bento Framework（开发模式）..."
	$(PIP) install -e ".[dev]"

# 检查包
check: build
	@echo "🔍 检查包..."
	$(PYTHON) -m twine check dist/*
	@echo "✅ 包检查通过"

# 发布到 Test PyPI
publish-test: build check
	@echo "🚀 发布到 Test PyPI..."
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo "✅ 发布到 Test PyPI 完成"
	@echo "📦 测试安装: pip install --index-url https://test.pypi.org/simple/ bento-framework"

# 发布到 PyPI
publish: build check
	@echo "🚀 发布到 PyPI..."
	@read -p "确认发布到 PyPI? [y/N] " confirm && [ "$$confirm" = "y" ]
	$(PYTHON) -m twine upload dist/*
	@echo "✅ 发布到 PyPI 完成"
	@echo "📦 安装: pip install bento-framework"

# 完整发布流程
release: clean
	@echo "🎉 开始发布流程..."
	@echo ""
	@echo "1️⃣  运行测试..."
	$(MAKE) test-cov
	@echo ""
	@echo "2️⃣  代码检查..."
	$(MAKE) lint
	@echo ""
	@echo "3️⃣  构建包..."
	$(MAKE) build
	@echo ""
	@echo "4️⃣  检查包..."
	$(MAKE) check
	@echo ""
	@echo "✅ 发布准备完成！"
	@echo ""
	@echo "下一步："
	@echo "  1. 更新 CHANGELOG.md"
	@echo "  2. 创建 git tag: git tag v0.1.0"
	@echo "  3. 推送标签: git push origin v0.1.0"
	@echo "  4. 或手动发布: make publish"

# 运行示例应用
run:
	@echo "🚀 运行示例应用..."
	uv run examples/minimal_app/main.py

# 开发模式
dev:
	@echo "🔧 启动开发服务器..."
	uvicorn examples.minimal_app.main:app --reload
