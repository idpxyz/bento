.PHONY: all build generate register docs serve-docs install lint clean help version-new version-list verify-compatibility test convert-md schema-check schema-monitor schema-monitor-init api api-dev api-prod api
.DEFAULT_GOAL := help

# 定义 Schema 目录
SCHEMA_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

# 默认目标
all: build generate docs


# 安装依赖
install:
	@echo "🔧 安装依赖..."
	pip install pydantic==2.* pyyaml requests mkdocs-material pytest pytest-asyncio markdown beautifulsoup4

# 编译 schema
build:
	@echo "🔨 编译 schema..."
	python -m idp.framework.infrastructure.schema.cli.schemactl build

# 生成 Pydantic 模型
generate:
	@echo "🔄 生成 Pydantic 模型..."
	python -m idp.framework.infrastructure.schema.cli.schemactl generate

# 注册 schema 到 Schema Registry
register:
	@echo "📡 注册 schema 到 Pulsar Schema Registry..."
	@# 优先使用小写 url，如果没有则使用大写 URL
	@URL_VALUE=""; \
	if [ -n "$(url)" ]; then \
		URL_VALUE="$(url)"; \
	elif [ -n "$(URL)" ]; then \
		URL_VALUE="$(URL)"; \
	fi; \
	\
	# 如果 URL 以 pulsar:// 开头，尝试自动转换为 Admin HTTP URL \
	if echo "$$URL_VALUE" | grep -q "^pulsar://"; then \
		HOST_PORT=$$(echo "$$URL_VALUE" | sed 's|^pulsar://||'); \
		HOST=$$(echo "$$HOST_PORT" | cut -d':' -f1); \
		echo "⚠️ 检测到 Pulsar 协议 URL，将自动转换为 Admin HTTP URL"; \
		echo "  - 原始 URL: $$URL_VALUE"; \
		URL_VALUE="http://$$HOST:8080"; \
		echo "  - 转换后 URL: $$URL_VALUE"; \
	fi; \
	\
	# 验证 URL 格式是否为 HTTP \
	if [ -n "$$URL_VALUE" ]; then \
		if ! echo "$$URL_VALUE" | grep -q "^http"; then \
			echo "⚠️ URL 应该以 http:// 或 https:// 开头"; \
			echo "  请使用 Pulsar Admin HTTP URL (默认端口 8080)，而不是 Pulsar 协议 URL (默认端口 6650)"; \
			echo "  例如: http://192.168.8.137:8080"; \
			URL_VALUE="http://$$URL_VALUE"; \
			echo "  尝试自动修复为: $$URL_VALUE"; \
		fi; \
		python -m idp.framework.infrastructure.schema.cli.schemactl register --url $$URL_VALUE; \
	else \
		python -m idp.framework.infrastructure.schema.cli.schemactl register; \
	fi

# 转换 Markdown 到 HTML
convert-md:
	@echo "📄 转换 Markdown 文件到 HTML..."
	@if [ -f "USAGE.md" ]; then \
		echo "📝 处理使用指南..."; \
		mkdir -p $(SCHEMA_DIR)/docs/guides; \
		cp USAGE.md $(SCHEMA_DIR)/docs/guides/usage.md; \
		mkdir -p $(SCHEMA_DIR)/generated/html; \
		cp USAGE.md $(SCHEMA_DIR)/generated/html/usage.md; \
		python -c "import sys; sys.path.append('/workspace'); from src.idp.framework.infrastructure.schema.cli.schemactl import generate_html_from_md; generate_html_from_md('$(SCHEMA_DIR)/generated/html/usage.md', '$(SCHEMA_DIR)/generated/html/usage.html', 'Schema Center 使用指南')"; \
		cd $(SCHEMA_DIR)/generated/html && ln -sf usage.html how-to-use.html 2>/dev/null || true; \
	fi

# 生成文档
docs: convert-md
	@echo "📝 生成 schema 文档..."
	python -m idp.framework.infrastructure.schema.cli.schemactl docs

# 启动文档服务
serve-docs: convert-md
	@echo "🚀 启动文档服务器，访问 http://localhost:8000 查看文档"
	@cd $(SCHEMA_DIR)/generated/html && python -m http.server 8000

# 创建新的 Schema (使用方式: make create NAME=EventName FORMAT=proto DESC="描述")
create:
	@if [ -z "$(NAME)" ]; then \
		echo "❌ 缺少参数: make create NAME=EventName FORMAT=proto DESC=\"描述\""; \
		exit 1; \
	fi
	@echo "🆕 创建新 Schema: $(NAME)..."
	python -m idp.framework.infrastructure.schema.cli.schemactl create \
		--name $(NAME) \
		--format $(FORMAT) \
		--desc "$(DESC)"

# 创建新版本 Schema (使用方式: make version-new NAME=EventName VERSION=2)
version-new:
	@if [ -z "$(NAME)" ] || [ -z "$(VERSION)" ]; then \
		echo "❌ 缺少参数: make version-new NAME=EventName VERSION=2"; \
		exit 1; \
	fi
	@echo "🔖 创建 Schema 新版本: $(NAME) v$(VERSION)..."
	python -m idp.framework.infrastructure.schema.cli.schemactl version-new \
		--name $(NAME) \
		--version $(VERSION)

# 列出 Schema 的所有版本 (使用方式: make version-list NAME=EventName)
version-list:
	@if [ -z "$(NAME)" ]; then \
		echo "❌ 缺少参数: make version-list NAME=EventName"; \
		exit 1; \
	fi
	@echo "📋 列出 Schema 版本: $(NAME)..."
	python -m idp.framework.infrastructure.schema.cli.schemactl version-list \
		--name $(NAME)

# 验证 Schema 兼容性 (使用方式: make verify-compatibility NAME=EventName VERSION=2 MODE=BACKWARD)
verify-compatibility:
	@if [ -z "$(NAME)" ] || [ -z "$(VERSION)" ]; then \
		echo "❌ 缺少参数: make verify-compatibility NAME=EventName VERSION=2 MODE=BACKWARD"; \
		exit 1; \
	fi
	@if [ -z "$(MODE)" ]; then \
		MODE="BACKWARD"; \
	fi
	@echo "🔍 验证 Schema 兼容性: $(NAME) v$(VERSION) ($(MODE))..."
	python -m idp.framework.infrastructure.schema.cli.schemactl verify-compatibility \
		--name $(NAME) \
		--version $(VERSION) \
		--mode $(MODE)

# 运行单元测试
test:
	@echo "🧪 运行单元测试..."
	pytest -xvs tests/

# 检查 schema 文件
lint:
	@echo "🔍 检查 schema 文件格式..."
	find proto -name "*.proto" -exec protoc --proto_path=. {} \;
	find avro -name "*.avsc" -exec python -c "import json; json.load(open('{}'))" \;
	find json -name "*.json" -exec python -c "import json; json.load(open('{}'))" \;

# 清理生成的文件
clean:
	@echo "🧹 清理生成的文件..."
	rm -rf generated/models/*
	rm -rf generated/proto/*
	rm -rf docs/schemas/*
	find . -name "__pycache__" -exec rm -rf {} +

# Schema 监控命令
schema-check:
	@echo "🔍 检查 Schema 健康状态..."
	python -m idp.framework.infrastructure.schema.monitor.schema_monitor_cli check $(if $(url),--url $(url),)

schema-monitor:
	@echo "📡 启动 Schema 监控服务..."
	python -m idp.framework.infrastructure.schema.monitor.schema_monitor_cli start $(if $(url),--url $(url),) $(if $(interval),--interval $(interval),)

# 设置必要的目录
schema-monitor-init:
	@echo "🛠️ 初始化 Schema 监控环境..."
	@mkdir -p $(SCHEMA_DIR)/monitor
	@touch $(SCHEMA_DIR)/monitor/schema_monitor.log
	@touch $(SCHEMA_DIR)/monitor/schema_monitor_errors.log

# 帮助信息
help:
	@echo "Schema 管理工具命令:"
	@echo ""
	@echo "  make install      - 安装依赖"
	@echo "  make build        - 编译所有 schema"
	@echo "  make generate     - 生成 Pydantic 模型"
	@echo "  make register     - 注册 schema 到 Pulsar Schema Registry"
	@echo "    支持两种参数方式: make register URL=http://192.168.1.1:8080 或 make register url=http://192.168.1.1:8080"
	@echo "    注意: 必须使用 Pulsar Admin HTTP URL (默认端口 8080)，而不是 Pulsar 协议 URL (默认端口 6650)"
	@echo "  make docs         - 生成文档"
	@echo "  make serve-docs   - 启动文档服务器"
	@echo "  make convert-md   - 转换 Markdown 文件到 HTML"
	@echo "  make create NAME=EventName FORMAT=proto DESC=\"描述\" - 创建新 Schema"
	@echo "  make lint         - 检查 schema 文件"
	@echo "  make clean        - 清理生成的文件"
	@echo "  make all          - 执行 build, generate 和 docs"
	@echo ""
	@echo "版本控制与兼容性:"
	@echo "  make version-new NAME=EventName VERSION=2 - 创建 Schema 新版本"
	@echo "  make version-list NAME=EventName - 列出 Schema 的所有版本"
	@echo "  make verify-compatibility NAME=EventName VERSION=2 MODE=BACKWARD - 验证 Schema 兼容性"
	@echo "  make test - 运行单元测试"
	@echo ""
	@echo "兼容性模式(MODE):"
	@echo "  BACKWARD - 新版本可以读取旧版本数据 (默认)"
	@echo "  FORWARD  - 旧版本可以读取新版本数据"
	@echo "  FULL     - 完全兼容 (BACKWARD + FORWARD)"
	@echo "  NONE     - 不要求兼容性"
	@echo ""
	@echo "示例:"
	@echo "  make create NAME=UserLoggedIn FORMAT=proto DESC=\"用户登录事件\""
	@echo "  make version-new NAME=UserLoggedIn VERSION=2"
	@echo "  make verify-compatibility NAME=UserLoggedIn VERSION=2 MODE=BACKWARD"
	@echo "  make all"
	@echo ""
	@echo "环境变量:"
	@echo "  PULSAR_ADMIN_URL  - Pulsar Admin API URL (用于 register 命令)"
	@echo ""
	@echo "Schema 监控命令:"
	@echo "  make schema-check - 检查 Schema 健康状态"
	@echo "  make schema-monitor - 启动 Schema 监控服务"
	@echo "  make schema-monitor-init - 初始化 Schema 监控环境"
	@echo ""
	@echo "示例"
	@echo "  make schema-monitor url=http://192.168.1.1:8080 interval=10"
	@echo "  make schema-check url=http://192.168.1.1:8080"
	@echo "  make schema-monitor-init url=http://192.168.1.1:8080"

# Schema 监控 API
.PHONY: api api-dev api-prod

# 启动Schema监控API服务（开发模式）
api-dev:
	@echo "启动Schema监控API服务 (开发模式)"
	python -m idp.framework.api.schema.cli --host 0.0.0.0 --port 8000 --reload --debug

# 启动Schema监控API服务（生产模式）
api-prod:
	@echo "启动Schema监控API服务 (生产模式)"
	python -m idp.framework.api.schema.cli --host 0.0.0.0 --port 8000

# 启动Schema监控API服务（默认开发模式）
api: api-dev




