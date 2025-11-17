#!/bin/bash
# 验证 VS Code 配置是否符合 Bento 项目标准

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔍 验证 VS Code 配置..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNINGS=0

# 检查函数
check_file_exists() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file (不存在)"
        ((FAILED++))
        return 1
    fi
}

check_json_key() {
    local file=$1
    local key=$2
    local expected=$3
    local description=$4

    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} $description: 文件不存在"
        ((FAILED++))
        return 1
    fi

    local actual=$(cat "$file" | grep -o "\"$key\"" | wc -l)

    if [ "$actual" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description: 缺少 $key"
        ((FAILED++))
        return 1
    fi
}

check_formatter() {
    local file=$1
    local description=$2

    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} $description: 文件不存在"
        ((FAILED++))
        return 1
    fi

    if grep -q '"editor.defaultFormatter": "charliermarsh.ruff"' "$file"; then
        echo -e "${GREEN}✓${NC} $description: 使用 Ruff 格式化"
        ((PASSED++))
    elif grep -q '"editor.defaultFormatter": "ms-python.black-formatter"' "$file"; then
        echo -e "${RED}✗${NC} $description: 错误使用 Black (应使用 Ruff)"
        ((FAILED++))
        return 1
    else
        echo -e "${YELLOW}⚠${NC} $description: 未配置格式化工具"
        ((WARNINGS++))
        return 1
    fi
}

check_makefile_command() {
    local makefile=$1
    local command=$2
    local description=$3

    if [ ! -f "$makefile" ]; then
        echo -e "${RED}✗${NC} $description: Makefile 不存在"
        ((FAILED++))
        return 1
    fi

    if grep -q "^$command:" "$makefile"; then
        echo -e "${GREEN}✓${NC} $description: make $command"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description: 缺少 make $command"
        ((FAILED++))
        return 1
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  检查项目根目录配置（标准参考）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

check_file_exists "$ROOT_DIR/.vscode/extensions.json" "扩展推荐"
check_file_exists "$ROOT_DIR/.vscode/settings.json" "VS Code 设置"
check_file_exists "$ROOT_DIR/.vscode/tasks.json" "任务配置"
check_file_exists "$ROOT_DIR/Makefile" "Makefile"

echo ""
check_formatter "$ROOT_DIR/.vscode/settings.json" "项目根目录"
check_json_key "$ROOT_DIR/.vscode/extensions.json" "charliermarsh.ruff" "" "推荐 Ruff 扩展"
check_json_key "$ROOT_DIR/.vscode/extensions.json" "unwantedRecommendations" "" "排除冲突扩展"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  检查 my-shop 项目配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

check_file_exists "$ROOT_DIR/applications/my-shop/.vscode/extensions.json" "扩展推荐"
check_file_exists "$ROOT_DIR/applications/my-shop/.vscode/settings.json" "VS Code 设置"
check_file_exists "$ROOT_DIR/applications/my-shop/.vscode/tasks.json" "任务配置"
check_file_exists "$ROOT_DIR/applications/my-shop/.vscode/launch.json" "调试配置"
check_file_exists "$ROOT_DIR/applications/my-shop/Makefile" "Makefile"

echo ""
check_formatter "$ROOT_DIR/applications/my-shop/.vscode/settings.json" "my-shop"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  检查 CLI 模板"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

check_file_exists "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/extensions.json.tpl" "扩展模板"
check_file_exists "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/settings.json.tpl" "设置模板"
check_file_exists "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/tasks.json.tpl" "任务模板"
check_file_exists "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/launch.json.tpl" "调试模板"
check_file_exists "$ROOT_DIR/src/bento/toolkit/templates/project/Makefile.tpl" "Makefile 模板"

echo ""
check_formatter "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/settings.json.tpl" "CLI 模板"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  检查 Makefile 命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for cmd in fmt lint test test-cov clean dev; do
    check_makefile_command "$ROOT_DIR/Makefile" "$cmd" "项目根目录"
    check_makefile_command "$ROOT_DIR/applications/my-shop/Makefile" "$cmd" "my-shop"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  配置一致性检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查扩展推荐是否一致
ROOT_RUFF=$(grep -c "charliermarsh.ruff" "$ROOT_DIR/.vscode/extensions.json" || echo 0)
MYSHOP_RUFF=$(grep -c "charliermarsh.ruff" "$ROOT_DIR/applications/my-shop/.vscode/extensions.json" || echo 0)
TEMPLATE_RUFF=$(grep -c "charliermarsh.ruff" "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/extensions.json.tpl" || echo 0)

if [ "$ROOT_RUFF" -gt 0 ] && [ "$MYSHOP_RUFF" -gt 0 ] && [ "$TEMPLATE_RUFF" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} 所有配置都推荐 Ruff 扩展"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Ruff 扩展推荐不一致"
    ((FAILED++))
fi

# 检查是否排除了 Black
ROOT_NOBLOCK=$(grep -c "black-formatter" "$ROOT_DIR/.vscode/extensions.json" || echo 0)
MYSHOP_NOBLOCK=$(grep -c "black-formatter" "$ROOT_DIR/applications/my-shop/.vscode/extensions.json" || echo 0)
TEMPLATE_NOBLOCK=$(grep -c "black-formatter" "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/extensions.json.tpl" || echo 0)

if [ "$ROOT_NOBLOCK" -gt 0 ] && [ "$MYSHOP_NOBLOCK" -gt 0 ] && [ "$TEMPLATE_NOBLOCK" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} 所有配置都排除了 Black"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Black 排除不一致"
    ((FAILED++))
fi

# 检查任务是否使用 Makefile
ROOT_MAKE_TASKS=$(grep -c '"command": "make ' "$ROOT_DIR/.vscode/tasks.json" || echo 0)
MYSHOP_MAKE_TASKS=$(grep -c '"command": "make ' "$ROOT_DIR/applications/my-shop/.vscode/tasks.json" || echo 0)
TEMPLATE_MAKE_TASKS=$(grep -c '"command": "make ' "$ROOT_DIR/src/bento/toolkit/templates/project/vscode/tasks.json.tpl" || echo 0)

if [ "$ROOT_MAKE_TASKS" -ge 4 ] && [ "$MYSHOP_MAKE_TASKS" -ge 4 ] && [ "$TEMPLATE_MAKE_TASKS" -ge 4 ]; then
    echo -e "${GREEN}✓${NC} 所有任务都使用 Makefile 命令"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} 任务配置可能不完整 (root:$ROOT_MAKE_TASKS, my-shop:$MYSHOP_MAKE_TASKS, template:$TEMPLATE_MAKE_TASKS)"
    ((WARNINGS++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 验证结果"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${YELLOW}警告: $WARNINGS${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！配置完全符合 Bento 项目标准。${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  配置基本正确，但有 $WARNINGS 个警告。${NC}"
    exit 0
else
    echo -e "${RED}❌ 发现 $FAILED 个问题，需要修复。${NC}"
    exit 1
fi
