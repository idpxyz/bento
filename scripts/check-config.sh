#!/bin/bash
# 快速验证 VS Code 配置

ROOT="/workspace/bento"
PASS=0
FAIL=0

echo "🔍 VS Code 配置验证"
echo "══════════════════════════════════════"
echo ""

# 1. 检查格式化工具
echo "1️⃣  格式化工具配置"
if grep -q '"editor.defaultFormatter": "charliermarsh.ruff"' "$ROOT/.vscode/settings.json" && \
   grep -q '"editor.defaultFormatter": "charliermarsh.ruff"' "$ROOT/applications/my-shop/.vscode/settings.json" && \
   grep -q '"editor.defaultFormatter": "charliermarsh.ruff"' "$ROOT/src/bento/toolkit/templates/project/vscode/settings.json.tpl"; then
    echo "✅ 所有配置使用 Ruff 格式化"
    ((PASS++))
else
    echo "❌ 格式化工具配置不一致"
    ((FAIL++))
fi

# 2. 检查扩展推荐
echo ""
echo "2️⃣  扩展推荐"
if grep -q '"charliermarsh.ruff"' "$ROOT/.vscode/extensions.json" && \
   grep -q '"charliermarsh.ruff"' "$ROOT/applications/my-shop/.vscode/extensions.json" && \
   grep -q '"charliermarsh.ruff"' "$ROOT/src/bento/toolkit/templates/project/vscode/extensions.json.tpl"; then
    echo "✅ 推荐 Ruff 扩展"
    ((PASS++))
else
    echo "❌ Ruff 扩展推荐缺失"
    ((FAIL++))
fi

if grep -q '"unwantedRecommendations"' "$ROOT/.vscode/extensions.json" && \
   grep -q '"unwantedRecommendations"' "$ROOT/applications/my-shop/.vscode/extensions.json" && \
   grep -q '"unwantedRecommendations"' "$ROOT/src/bento/toolkit/templates/project/vscode/extensions.json.tpl"; then
    echo "✅ 排除冲突扩展 (Black, Flake8)"
    ((PASS++))
else
    echo "❌ 未排除冲突扩展"
    ((FAIL++))
fi

# 3. 检查任务配置
echo ""
echo "3️⃣  任务配置"
if grep -q '"command": "make test"' "$ROOT/.vscode/tasks.json" && \
   grep -q '"command": "make test"' "$ROOT/applications/my-shop/.vscode/tasks.json" && \
   grep -q '"command": "make test"' "$ROOT/src/bento/toolkit/templates/project/vscode/tasks.json.tpl"; then
    echo "✅ 使用 Makefile 命令"
    ((PASS++))
else
    echo "❌ 任务未使用 Makefile"
    ((FAIL++))
fi

# 4. 检查 Makefile
echo ""
echo "4️⃣  Makefile 命令"
MAKEFILE_CMDS="fmt lint test test-cov dev clean"
ALL_FOUND=true
for cmd in $MAKEFILE_CMDS; do
    if ! grep -q "^$cmd:" "$ROOT/Makefile" || ! grep -q "^$cmd:" "$ROOT/applications/my-shop/Makefile"; then
        ALL_FOUND=false
        break
    fi
done

if $ALL_FOUND; then
    echo "✅ 所有必需命令存在: $MAKEFILE_CMDS"
    ((PASS++))
else
    echo "❌ Makefile 命令不完整"
    ((FAIL++))
fi

# 5. 检查 PYTHONPATH 配置
echo ""
echo "5️⃣  PYTHONPATH 配置"
if grep -q '"terminal.integrated.env.linux"' "$ROOT/.vscode/settings.json" && \
   grep -q '"terminal.integrated.env.linux"' "$ROOT/applications/my-shop/.vscode/settings.json"; then
    echo "✅ 跨平台 PYTHONPATH 配置正确"
    ((PASS++))
else
    echo "❌ PYTHONPATH 配置缺失"
    ((FAIL++))
fi

# 总结
echo ""
echo "══════════════════════════════════════"
echo "📊 验证结果: $PASS 通过 / $FAIL 失败"
echo "══════════════════════════════════════"

if [ $FAIL -eq 0 ]; then
    echo "✅ 所有检查通过！"
    exit 0
else
    echo "❌ 发现 $FAIL 个问题"
    exit 1
fi
