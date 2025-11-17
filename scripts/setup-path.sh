#!/bin/bash
# 将 Bento CLI 添加到 PATH

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BENTO_ROOT="$(dirname "$SCRIPT_DIR")"
BENTO_BIN="$BENTO_ROOT/bin"

echo "🔧 Bento CLI 路径设置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检测 shell
SHELL_NAME=$(basename "$SHELL")
if [ "$SHELL_NAME" = "bash" ]; then
    RC_FILE="$HOME/.bashrc"
elif [ "$SHELL_NAME" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
else
    echo "⚠️  未知的 shell: $SHELL_NAME"
    echo "请手动添加以下内容到您的 shell 配置文件："
    echo ""
    echo "export PATH=\"$BENTO_BIN:\$PATH\""
    exit 1
fi

echo "检测到 shell: $SHELL_NAME"
echo "配置文件: $RC_FILE"
echo ""

# 检查是否已添加
if grep -q "bento/bin" "$RC_FILE" 2>/dev/null; then
    echo "✅ Bento CLI 已经在 PATH 中"
    echo ""
    echo "当前配置:"
    grep "bento/bin" "$RC_FILE"
    echo ""
    echo "如需重新配置，请手动编辑: $RC_FILE"
    exit 0
fi

# 询问是否添加
echo "将要添加以下内容到 $RC_FILE:"
echo ""
echo "  # Bento Framework CLI"
echo "  export PATH=\"$BENTO_BIN:\$PATH\""
echo ""
read -p "是否继续? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# 添加到配置文件
echo "" >> "$RC_FILE"
echo "# Bento Framework CLI" >> "$RC_FILE"
echo "export PATH=\"$BENTO_BIN:\$PATH\"" >> "$RC_FILE"

echo "✅ 已添加到 $RC_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 下一步:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 重新加载配置:"
echo "   source $RC_FILE"
echo ""
echo "2. 或者重启终端"
echo ""
echo "3. 验证安装:"
echo "   which bento"
echo "   bento --help"
echo ""
