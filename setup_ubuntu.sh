#!/bin/bash
# Bento Framework - Ubuntu 环境配置脚本
# 用途：从 Windows 迁移到 Ubuntu 后的快速环境配置

set -e  # 遇到错误立即退出

echo "=========================================="
echo "Bento Framework - Ubuntu 环境配置"
echo "=========================================="
echo ""
echo "请选择开发模式:"
echo "  1) Docker 部署（推荐）- 所有服务在容器中运行"
echo "  2) 本地开发 - 在宿主机上安装所有服务"
echo "  3) 混合模式 - Docker + 本地服务"
echo ""
read -p "请输入选择 (1/2/3) [默认: 1]: " DEV_MODE
DEV_MODE=${DEV_MODE:-1}
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 Ubuntu/Debian
if [ ! -f /etc/debian_version ]; then
    echo -e "${RED}警告: 此脚本主要为 Ubuntu/Debian 设计${NC}"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. 检查 Python 版本
echo -e "${YELLOW}[1/8] 检查 Python 版本...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python 已安装: $PYTHON_VERSION${NC}"
    
    # 检查是否为 3.12.x
    if [[ ! $PYTHON_VERSION =~ ^3\.12\. ]]; then
        echo -e "${YELLOW}  警告: 项目要求 Python 3.12.x，当前版本为 $PYTHON_VERSION${NC}"
        echo "  请考虑安装 Python 3.12:"
        echo "  sudo add-apt-repository ppa:deadsnakes/ppa"
        echo "  sudo apt update"
        echo "  sudo apt install python3.12 python3.12-venv python3.12-dev"
    fi
else
    echo -e "${RED}✗ Python 未安装${NC}"
    echo "  请安装 Python 3.12:"
    echo "  sudo apt update"
    echo "  sudo apt install python3.12 python3.12-venv python3.12-dev"
    exit 1
fi

# 2. 安装系统依赖
echo ""
echo -e "${YELLOW}[2/8] 检查系统依赖...${NC}"
MISSING_DEPS=()

# 检查必要的包
REQUIRED_PACKAGES=("build-essential" "libssl-dev" "libpq-dev" "git" "curl")
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! dpkg -l | grep -q "^ii  $pkg"; then
        MISSING_DEPS+=("$pkg")
    fi
done

if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ 所有系统依赖已安装${NC}"
else
    echo -e "${YELLOW}  缺少以下依赖: ${MISSING_DEPS[*]}${NC}"
    read -p "是否安装缺少的依赖? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt update
        sudo apt install -y "${MISSING_DEPS[@]}"
        echo -e "${GREEN}✓ 依赖安装完成${NC}"
    fi
fi

# 3. 安装 uv
echo ""
echo -e "${YELLOW}[3/8] 检查 uv (Python 包管理器)...${NC}"
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ uv 已安装: $UV_VERSION${NC}"
else
    echo "  uv 未安装，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # 添加到当前会话的 PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if command -v uv &> /dev/null; then
        echo -e "${GREEN}✓ uv 安装成功${NC}"
        echo "  请运行以下命令将 uv 添加到 PATH:"
        echo "  echo 'export PATH=\"\$HOME/.cargo/bin:\$PATH\"' >> ~/.bashrc"
        echo "  source ~/.bashrc"
    else
        echo -e "${RED}✗ uv 安装失败${NC}"
    fi
fi

# 4. 检查 PostgreSQL（根据开发模式）
echo ""
echo -e "${YELLOW}[4/8] 检查 PostgreSQL...${NC}"
if [ "$DEV_MODE" = "1" ]; then
    # Docker 模式 - 只需要客户端工具（可选）
    echo -e "${BLUE}  Docker 模式: PostgreSQL 将在容器中运行${NC}"
    if command -v psql &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL 客户端已安装（用于调试）${NC}"
    else
        echo -e "${YELLOW}  PostgreSQL 客户端未安装${NC}"
        read -p "是否安装 PostgreSQL 客户端工具？(用于调试，可选) (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt install -y postgresql-client
            echo -e "${GREEN}✓ PostgreSQL 客户端安装完成${NC}"
        fi
    fi
elif [ "$DEV_MODE" = "2" ] || [ "$DEV_MODE" = "3" ]; then
    # 本地开发或混合模式 - 需要完整的 PostgreSQL
    if command -v psql &> /dev/null; then
        PSQL_VERSION=$(psql --version | cut -d' ' -f3)
        echo -e "${GREEN}✓ PostgreSQL 已安装: $PSQL_VERSION${NC}"
    else
        echo -e "${YELLOW}  PostgreSQL 未安装${NC}"
        read -p "是否安装 PostgreSQL? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt install -y postgresql postgresql-contrib
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            echo -e "${GREEN}✓ PostgreSQL 安装完成${NC}"
        fi
    fi
fi

# 5. 检查 Redis（根据开发模式）
echo ""
echo -e "${YELLOW}[5/8] 检查 Redis...${NC}"
if [ "$DEV_MODE" = "1" ]; then
    # Docker 模式 - 只需要客户端工具（可选）
    echo -e "${BLUE}  Docker 模式: Redis 将在容器中运行${NC}"
    if command -v redis-cli &> /dev/null; then
        echo -e "${GREEN}✓ Redis 客户端已安装（用于调试）${NC}"
    else
        echo -e "${YELLOW}  Redis 客户端未安装${NC}"
        read -p "是否安装 Redis 客户端工具？(用于调试，可选) (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt install -y redis-tools
            echo -e "${GREEN}✓ Redis 客户端安装完成${NC}"
        fi
    fi
elif [ "$DEV_MODE" = "2" ] || [ "$DEV_MODE" = "3" ]; then
    # 本地开发或混合模式 - 需要完整的 Redis
    if command -v redis-cli &> /dev/null; then
        REDIS_VERSION=$(redis-cli --version | cut -d' ' -f2)
        echo -e "${GREEN}✓ Redis 已安装: $REDIS_VERSION${NC}"
        
        # 检查 Redis 是否运行
        if systemctl is-active --quiet redis-server 2>/dev/null || systemctl is-active --quiet redis 2>/dev/null; then
            echo -e "${GREEN}  Redis 服务正在运行${NC}"
        else
            echo -e "${YELLOW}  Redis 服务未运行${NC}"
            read -p "是否启动 Redis? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null
                sudo systemctl enable redis-server 2>/dev/null || sudo systemctl enable redis 2>/dev/null
                echo -e "${GREEN}  Redis 已启动${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}  Redis 未安装${NC}"
        read -p "是否安装 Redis? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt install -y redis-server
            sudo systemctl start redis-server
            sudo systemctl enable redis-server
            echo -e "${GREEN}✓ Redis 安装完成${NC}"
        fi
    fi
fi

# 6. 安装 Python 依赖
echo ""
echo -e "${YELLOW}[6/8] 安装 Python 项目依赖...${NC}"
if [ -f "pyproject.toml" ]; then
    if command -v uv &> /dev/null; then
        echo "  使用 uv 安装依赖..."
        uv sync
        echo -e "${GREEN}✓ Python 依赖安装完成${NC}"
    else
        echo "  使用 pip 安装依赖..."
        python3 -m pip install -e ".[dev]"
        echo -e "${GREEN}✓ Python 依赖安装完成${NC}"
    fi
else
    echo -e "${RED}✗ 未找到 pyproject.toml${NC}"
fi

# 7. 创建环境变量文件
echo ""
echo -e "${YELLOW}[7/8] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    echo "  创建 .env 文件..."
    if [ "$DEV_MODE" = "1" ]; then
        # Docker 模式 - 使用容器服务名
        cat > .env << 'EOF'
# Docker 模式配置
# 数据库配置（容器内服务）
DB_HOST=postgres
DB_PORT=5432
DB_NAME=bento_db
DB_USER=app
DB_PASSWORD=app

# Redis 配置（容器内服务）
REDIS_URL=redis://redis:6379/0

# Pulsar 配置 (如果启用)
# PULSAR_URL=pulsar://redpanda:9092

# 应用配置
ENV=dev
DEBUG=true
EOF
        echo -e "${GREEN}✓ .env 文件已创建（Docker 模式）${NC}"
        echo -e "${BLUE}  注意: 使用的是 Docker 容器服务名（postgres, redis）${NC}"
    else
        # 本地开发模式 - 使用 localhost
        cat > .env << 'EOF'
# 本地开发模式配置
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=idp_dev
DB_USER=postgres
DB_PASSWORD=thends

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# Pulsar 配置 (如果启用)
# PULSAR_URL=pulsar://localhost:6650

# 应用配置
ENV=dev
DEBUG=true
EOF
        echo -e "${GREEN}✓ .env 文件已创建（本地模式）${NC}"
        echo -e "${YELLOW}  请根据实际情况修改数据库密码和其他配置${NC}"
    fi
    
    # 添加到 .gitignore
    if ! grep -q "^.env$" .gitignore 2>/dev/null; then
        echo ".env" >> .gitignore
        echo "  .env 已添加到 .gitignore"
    fi
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi

# 8. 验证配置
echo ""
echo -e "${YELLOW}[8/8] 验证配置...${NC}"

if [ "$DEV_MODE" = "1" ]; then
    # Docker 模式 - 检查 Docker 是否可用
    if docker info &> /dev/null; then
        echo -e "${GREEN}✓ Docker 环境正常${NC}"
    else
        echo -e "${RED}✗ Docker 环境异常${NC}"
    fi
    
    # 测试 Redis 连接（如果安装了客户端工具）
    if command -v redis-cli &> /dev/null; then
        echo -e "${BLUE}  Redis 客户端已安装，可用于连接容器中的 Redis${NC}"
    fi
    
    # 测试 PostgreSQL 连接（如果安装了客户端工具）
    if command -v psql &> /dev/null; then
        echo -e "${BLUE}  PostgreSQL 客户端已安装，可用于连接容器中的数据库${NC}"
    fi
else
    # 本地开发模式 - 测试本地服务连接
    # 测试 Redis 连接
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping &> /dev/null; then
            echo -e "${GREEN}✓ Redis 连接正常${NC}"
        else
            echo -e "${RED}✗ Redis 连接失败${NC}"
        fi
    fi

    # 测试 PostgreSQL 连接
    if command -v psql &> /dev/null; then
        if PGPASSWORD=thends psql -h localhost -U postgres -d postgres -c '\q' &> /dev/null; then
            echo -e "${GREEN}✓ PostgreSQL 连接正常${NC}"
        else
            echo -e "${YELLOW}  PostgreSQL 连接失败 (可能需要配置密码或创建数据库)${NC}"
        fi
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}配置完成！${NC}"
echo "=========================================="
echo ""

if [ "$DEV_MODE" = "1" ]; then
    echo -e "${BLUE}Docker 开发模式已配置${NC}"
    echo ""
    echo "后续步骤:"
    echo "  1. 启动 Docker 服务:"
    echo "     cd deploy/docker"
    echo "     ./start.sh dev"
    echo ""
    echo "  2. 访问应用:"
    echo "     API: http://localhost:8000"
    echo "     文档: http://localhost:8000/docs"
    echo ""
    echo "  3. 查看日志:"
    echo "     ./start.sh --logs"
    echo ""
    echo "  4. 停止服务:"
    echo "     ./start.sh --down"
    echo ""
    echo "Docker 命令:"
    echo "  docker ps                 - 查看运行的容器"
    echo "  docker logs bento-app     - 查看应用日志"
    echo "  docker exec -it bento-app bash  - 进入容器"
else
    echo -e "${BLUE}本地开发模式已配置${NC}"
    echo ""
    echo "后续步骤:"
    echo "  1. 检查并修改 .env 文件中的配置"
    echo "  2. 检查 legend/config/database.yml 中的数据库配置"
    echo "  3. 运行测试: make test"
    echo "  4. 启动开发服务器: make dev"
    echo ""
    echo "常用命令:"
    echo "  make fmt    - 格式化代码"
    echo "  make lint   - 代码检查"
    echo "  make test   - 运行测试"
    echo "  make run    - 运行示例应用"
    echo "  make dev    - 启动开发服务器"
fi

echo ""
echo "查看完整迁移指南: cat MIGRATION_UBUNTU.md"
echo "快速命令参考: cat UBUNTU_QUICK_REF.md"
echo ""

