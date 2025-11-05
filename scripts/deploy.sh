#!/bin/bash
# 快速部署脚本

set -e

echo "🚀 开始部署 Bento E-commerce..."

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 进入 docker 配置目录
cd "$PROJECT_ROOT/deploy/docker" || exit 1

# 构建并启动服务
echo "📦 构建 Docker 镜像..."
docker compose -f compose.yml build

echo "🚀 启动服务..."
docker compose -f compose.yml up -d

echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
echo "🏥 检查服务健康状态..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 应用已成功启动！"
    echo "📍 API 地址: http://localhost:8000"
    echo "📊 健康检查: http://localhost:8000/health"
    echo ""
    echo "查看日志: docker compose -f compose.yml logs -f app"
else
    echo "⚠️  服务可能还在启动中，请检查日志: docker compose -f compose.yml logs app"
fi

echo ""
echo "✅ 部署完成！"

