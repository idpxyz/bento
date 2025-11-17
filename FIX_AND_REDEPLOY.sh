#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔧 CI/CD 修复和重新部署脚本${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查是否有未提交的更改
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}⚠️  发现未提交的更改${NC}"
    git status -s
    echo ""
    read -p "是否提交这些更改? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .github/workflows/release.yml
        git commit -m "fix: update release workflow for first release"
        echo -e "${GREEN}✅ 更改已提交${NC}"
    else
        echo -e "${RED}❌ 取消操作${NC}"
        exit 1
    fi
fi
echo ""

# 删除旧的 tag
echo -e "${BLUE}1️⃣  删除旧的 v0.1.0 tag...${NC}"
if git tag -l | grep -q "v0.1.0"; then
    git tag -d v0.1.0
    echo -e "${GREEN}✅ 本地 tag 已删除${NC}"

    if git ls-remote --tags origin | grep -q "v0.1.0"; then
        git push origin :refs/tags/v0.1.0
        echo -e "${GREEN}✅ 远程 tag 已删除${NC}"
    fi
else
    echo -e "${YELLOW}⏭  Tag 不存在，跳过${NC}"
fi
echo ""

# 推送修复
echo -e "${BLUE}2️⃣  推送 workflow 修复...${NC}"
git push origin main || git push origin master
echo -e "${GREEN}✅ 修复已推送${NC}"
echo ""

# 重新创建 tag
echo -e "${BLUE}3️⃣  重新创建 v0.1.0 tag...${NC}"
git tag v0.1.0
echo -e "${GREEN}✅ Tag 已创建${NC}"
echo ""

# 询问是否推送
echo -e "${YELLOW}准备推送 tag 并触发 CI/CD...${NC}"
echo ""
echo -e "${BLUE}注意事项:${NC}"
echo "1. 确保已配置 PYPI_API_TOKEN secret"
echo "   访问: https://github.com/idpxyz/bento/settings/secrets/actions"
echo ""
echo "2. 如果没有 PyPI token，workflow 会在发布步骤失败"
echo "   但 GitHub Release 仍会创建成功"
echo ""
echo "3. 可以稍后手动发布: make publish"
echo ""

read -p "是否立即推送 tag? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin v0.1.0
    echo ""
    echo -e "${GREEN}✅ Tag 已推送！${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 CI/CD 已触发！${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}📊 监控进度:${NC}"
    echo "   https://github.com/idpxyz/bento/actions"
    echo ""
    echo -e "${YELLOW}📦 查看 Release:${NC}"
    echo "   https://github.com/idpxyz/bento/releases/tag/v0.1.0"
    echo ""
    echo -e "${YELLOW}🔍 检查状态:${NC}"
    echo "   ./check-release.sh"
    echo ""
else
    echo ""
    echo -e "${YELLOW}⏸  Tag 未推送${NC}"
    echo ""
    echo "稍后可以手动推送:"
    echo "  git push origin v0.1.0"
    echo ""
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 完成！${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
