#!/bin/bash
# Bento Framework - Docker 快速启动脚本
# 适用于 Ubuntu/Linux 环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    cat << EOF
Bento Framework - Docker 启动脚本

用法: $0 [选项] [环境]

环境:
  prod           生产环境（默认）
  dev            开发环境（带热重载和额外服务）

选项:
  -h, --help     显示此帮助信息
  -b, --build    强制重新构建镜像
  -d, --down     停止并删除容器
  -l, --logs     查看日志
  --clean        清理所有数据（包括数据卷）

示例:
  $0 dev         启动开发环境
  $0 prod -b     重新构建并启动生产环境
  $0 -d          停止所有服务
  $0 -l          查看所有服务日志

EOF
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker 未安装${NC}"
        echo "请访问 https://docs.docker.com/engine/install/ubuntu/ 安装 Docker"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        echo -e "${RED}错误: Docker Compose 未安装或版本过旧${NC}"
        echo "请确保安装了 Docker Compose V2"
        exit 1
    fi

    echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
}

# 检查 Docker 守护进程是否运行
check_docker_daemon() {
    if ! docker info &> /dev/null; then
        echo -e "${RED}错误: Docker 守护进程未运行${NC}"
        echo "请启动 Docker 服务:"
        echo "  sudo systemctl start docker"
        exit 1
    fi
}

# 停止服务
stop_services() {
    echo -e "${YELLOW}停止所有服务...${NC}"
    docker compose -f compose.yml -f compose.dev.yaml down
    echo -e "${GREEN}✓ 服务已停止${NC}"
}

# 清理数据
clean_all() {
    echo -e "${RED}警告: 这将删除所有数据（包括数据库）！${NC}"
    read -p "确定要继续吗？(yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        echo -e "${YELLOW}清理所有数据...${NC}"
        docker compose -f compose.yml -f compose.dev.yaml down -v
        echo -e "${GREEN}✓ 数据已清理${NC}"
    else
        echo "已取消"
    fi
}

# 查看日志
show_logs() {
    echo -e "${BLUE}显示服务日志（Ctrl+C 退出）...${NC}"
    docker compose -f compose.yml -f compose.dev.yaml logs -f
}

# 启动生产环境
start_production() {
    local BUILD_FLAG=""
    if [ "$1" = "build" ]; then
        BUILD_FLAG="--build"
        echo -e "${YELLOW}重新构建镜像...${NC}"
    fi

    echo -e "${BLUE}启动生产环境...${NC}"
    docker compose -f compose.yml up -d $BUILD_FLAG

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ 生产环境启动成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "服务访问地址:"
    echo "  应用 API:    http://localhost:8000"
    echo "  PostgreSQL:  localhost:5432"
    echo "  Redis:       localhost:6379"
    echo ""
    echo "查看日志: docker compose -f compose.yml logs -f"
    echo "停止服务: docker compose -f compose.yml down"
}

# 启动开发环境
start_development() {
    local BUILD_FLAG=""
    if [ "$1" = "build" ]; then
        BUILD_FLAG="--build"
        echo -e "${YELLOW}重新构建镜像...${NC}"
    fi

    echo -e "${BLUE}启动开发环境...${NC}"
    docker compose -f compose.yml -f compose.dev.yaml up -d $BUILD_FLAG

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ 开发环境启动成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "服务访问地址:"
    echo "  应用 API:         http://localhost:8000"
    echo "  API 文档:         http://localhost:8000/docs"
    echo "  PostgreSQL:       localhost:5432"
    echo "  Redis:            localhost:6379"
    echo "  Redpanda (Kafka): localhost:19092"
    echo "  MinIO API:        http://localhost:9000"
    echo "  MinIO Console:    http://localhost:9001"
    echo ""
    echo "MinIO 凭据:"
    echo "  用户名: minio"
    echo "  密码:   minio123"
    echo ""
    echo "查看日志: docker compose -f compose.yml -f compose.dev.yaml logs -f"
    echo "停止服务: docker compose -f compose.yml -f compose.dev.yaml down"
}

# 主函数
main() {
    cd "$(dirname "$0")"  # 切换到脚本所在目录

    # 检查 Docker 环境
    check_docker
    check_docker_daemon

    local ENV="prod"
    local ACTION="start"
    local BUILD=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -b|--build)
                BUILD="build"
                shift
                ;;
            -d|--down)
                ACTION="down"
                shift
                ;;
            -l|--logs)
                ACTION="logs"
                shift
                ;;
            --clean)
                ACTION="clean"
                shift
                ;;
            prod|production)
                ENV="prod"
                shift
                ;;
            dev|development)
                ENV="dev"
                shift
                ;;
            *)
                echo -e "${RED}未知参数: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done

    # 执行操作
    case $ACTION in
        down)
            stop_services
            ;;
        clean)
            clean_all
            ;;
        logs)
            show_logs
            ;;
        start)
            if [ "$ENV" = "dev" ]; then
                start_development "$BUILD"
            else
                start_production "$BUILD"
            fi
            ;;
    esac
}

# 执行主函数
main "$@"

