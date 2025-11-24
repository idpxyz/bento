.PHONY: help fmt lint test test-cov clean dev

# Python 解释器（智能检测：优先虚拟环境）
PYTHON := $(shell \
	if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; \
	elif [ -f .venv/bin/python ]; then echo .venv/bin/python; \
	elif command -v python3 >/dev/null 2>&1; then echo python3; \
	else echo "python"; fi)

# 默认目标
help:
	@echo "my-shop - Makefile 命令"
	@echo ""
	@echo "Python: $(PYTHON)"
	@echo ""
	@echo "开发命令:"
	@echo "  make fmt          - 格式化代码（Ruff）"
	@echo "  make lint         - 代码检查（Ruff）"
	@echo "  make test         - 运行测试（Pytest）"
	@echo "  make test-cov     - 运行测试并生成覆盖率报告"
	@echo "  make dev          - 启动开发服务器（FastAPI）"
	@echo "  make clean        - 清理缓存和构建文件"
	@echo ""

# 代码格式化
fmt:
	@echo "🎨 格式化代码..."
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

# 代码检查
lint:
	@echo "🔍 代码检查..."
	$(PYTHON) -m ruff check .

# 运行测试
test:
	@echo "🧪 运行测试..."
	PYTHONPATH=.:../../src $(PYTHON) -m pytest tests/ -v

# 运行测试并生成覆盖率
test-cov:
	@echo "🧪 运行测试（带覆盖率）..."
	PYTHONPATH=.:../../src $(PYTHON) -m pytest tests/ --cov=contexts --cov-report=html --cov-report=term-missing
	@echo "📊 覆盖率报告: htmlcov/index.html"

# 清理构建文件
clean:
	@echo "🧹 清理缓存文件..."
	rm -rf htmlcov/ .coverage .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ 清理完成"

# 开发模式
dev:
	@echo "🔧 启动开发服务器..."
	PYTHONPATH=.:../../src $(PYTHON) -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
