# 多阶段构建 Dockerfile
# 使用 uv 作为包管理器
# 注意：构建上下文应该是项目根目录

# ========== 阶段 1: 构建阶段 ==========
FROM python:3.12-slim as builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml ./

# 创建虚拟环境并安装依赖（使用 uv pip，更快）
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python \
    "pydantic>=2.7,<3.0" \
    "fastapi>=0.115,<2.0" \
    "sqlalchemy[asyncio]>=2.0,<3.0" \
    "aiosqlite>=0.19.0" \
    "asyncpg>=0.29" \
    "alembic>=1.13" \
    "redis>=5.0,<6.0" \
    "tenacity>=8.2" \
    "python-dateutil>=2.8" \
    "uvicorn>=0.30,<1.0" \
    "httpx>=0.27"

# ========== 阶段 2: 运行阶段 ==========
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制应用代码
COPY --chown=appuser:appuser . .

# 切换到非 root 用户
USER appuser

# 设置环境变量
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5).raise_for_status()" || exit 1

# 启动命令
# 注意：实际应用路径请根据项目调整
# CMD ["uvicorn", "applications.ecommerce.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "examples.minimal_app.main:app", "--host", "0.0.0.0", "--port", "8000"]

