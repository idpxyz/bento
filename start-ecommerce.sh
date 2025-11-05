#!/bin/bash
# E-commerce 应用启动脚本 - 使用 uv（最简单版本）

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 启动 E-commerce 应用${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 切换到项目根目录
cd "$(dirname "$0")"

# 显示访问信息
echo -e "${BLUE}应用访问地址：${NC}"
echo -e "  ${GREEN}✓${NC} API 文档: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  ${GREEN}✓${NC} 健康检查: ${BLUE}http://localhost:8000/health${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止应用${NC}"
echo ""

# 使用 uv run 启动（自动处理虚拟环境和 PYTHONPATH）
uv run uvicorn applications.ecommerce.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000

