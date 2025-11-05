#!/bin/bash
# 部署到目标服务器的脚本
# 目标服务器: 192.168.8.196

set -e

# 配置
SERVER_IP="192.168.8.196"
SERVER_USER="${1:-$USER}"  # 从命令行参数获取用户名，或使用当前用户名
PROJECT_DIR="~/bento"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🚀 部署到服务器: $SERVER_USER@$SERVER_IP"
echo "📁 本地项目目录: $LOCAL_DIR"
echo "📁 服务器项目目录: $PROJECT_DIR"
echo ""

# 检查是否在项目根目录
if [ ! -f "$LOCAL_DIR/pyproject.toml" ]; then
    echo "❌ 错误: 未找到 pyproject.toml，请确保在项目根目录运行此脚本"
    exit 1
fi

# 询问部署方式
echo "请选择部署方式:"
echo "1) 使用 Git（推荐，需要服务器已克隆项目）"
echo "2) 使用 rsync 同步文件"
echo "3) 仅执行部署命令（文件已存在服务器）"
read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📦 使用 Git 部署..."
        echo "确保服务器上的项目已通过 Git 克隆"
        echo ""
        echo "在服务器上执行以下命令:"
        echo "  ssh $SERVER_USER@$SERVER_IP"
        echo "  cd $PROJECT_DIR"
        echo "  git pull"
        echo "  cd deploy/docker"
        echo "  docker compose -f compose.yml up -d --build"
        ;;
    2)
        echo ""
        echo "📤 使用 rsync 同步文件到服务器..."
        echo ""
        
        # 检查 rsync 是否可用
        if ! command -v rsync &> /dev/null; then
            echo "❌ rsync 未安装，请先安装:"
            echo "   macOS: brew install rsync"
            echo "   Linux: sudo apt-get install rsync"
            exit 1
        fi
        
        echo "正在同步文件（排除不需要的文件）..."
        rsync -avz --progress \
            --exclude '.git' \
            --exclude '.venv' \
            --exclude '__pycache__' \
            --exclude '*.pyc' \
            --exclude '.vscode' \
            --exclude '*.db' \
            --exclude '*.sqlite' \
            --exclude '.pytest_cache' \
            --exclude 'htmlcov' \
            --exclude 'dist' \
            --exclude 'build' \
            --exclude '*.egg-info' \
            "$LOCAL_DIR/" "$SERVER_USER@$SERVER_IP:$PROJECT_DIR/"
        
        echo ""
        echo "✅ 文件同步完成"
        echo ""
        echo "正在远程执行部署命令..."
        ssh "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
cd ~/bento
cd deploy/docker
docker compose -f compose.yml up -d --build
ENDSSH
        ;;
    3)
        echo ""
        echo "🚀 在服务器上执行部署命令..."
        ssh "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
cd ~/bento
cd deploy/docker
docker compose -f compose.yml up -d --build
ENDSSH
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 验证部署:"
echo "  curl http://$SERVER_IP:8000/health"
echo ""
echo "📊 查看日志:"
echo "  ssh $SERVER_USER@$SERVER_IP 'cd ~/bento/deploy/docker && docker compose -f compose.yml logs -f app'"

