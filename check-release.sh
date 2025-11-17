#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 检查 v0.1.0 发布状态${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. 检查 Git Tag
echo -e "${BLUE}1️⃣  检查 Git Tag${NC}"
if git tag | grep -q "v0.1.0"; then
    echo -e "${GREEN}✅ Tag v0.1.0 存在于本地${NC}"
else
    echo -e "${RED}❌ Tag v0.1.0 不存在于本地${NC}"
fi

if git ls-remote --tags origin | grep -q "v0.1.0"; then
    echo -e "${GREEN}✅ Tag v0.1.0 已推送到远程${NC}"
else
    echo -e "${RED}❌ Tag v0.1.0 未推送到远程${NC}"
fi
echo ""

# 2. 检查 GitHub Actions
echo -e "${BLUE}2️⃣  GitHub Actions 检查${NC}"
echo -e "   访问: ${YELLOW}https://github.com/idpxyz/bento/actions${NC}"
echo -e "   查找: ${YELLOW}Release v0.1.0${NC} workflow run"
echo ""

# 3. 检查 GitHub Releases
echo -e "${BLUE}3️⃣  GitHub Releases 检查${NC}"
echo -e "   访问: ${YELLOW}https://github.com/idpxyz/bento/releases${NC}"
echo -e "   查找: ${YELLOW}v0.1.0${NC} release"
echo ""

# 4. 检查 PyPI
echo -e "${BLUE}4️⃣  PyPI 发布检查${NC}"
if python3 -c "import urllib.request, json; data = json.loads(urllib.request.urlopen('https://pypi.org/pypi/bento-framework/json').read()); print(f'✅ 已发布到 PyPI: v{data[\"info\"][\"version\"]}')" 2>/dev/null; then
    echo -e "${GREEN}✅ 包已在 PyPI 上${NC}"
    echo -e "   安装: ${YELLOW}pip install bento-framework${NC}"
else
    echo -e "${YELLOW}⏳ 包尚未发布到 PyPI${NC}"
    echo -e "   ${YELLOW}可能原因:${NC}"
    echo -e "   - GitHub Actions 还在运行"
    echo -e "   - 需要配置 PYPI_API_TOKEN"
    echo -e "   - 发布失败（检查 Actions 日志）"
fi
echo ""

# 5. 快速链接
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔗 快速链接${NC}"
echo ""
echo -e "${GREEN}GitHub Actions:${NC}"
echo -e "   https://github.com/idpxyz/bento/actions"
echo ""
echo -e "${GREEN}GitHub Releases:${NC}"
echo -e "   https://github.com/idpxyz/bento/releases/tag/v0.1.0"
echo ""
echo -e "${GREEN}PyPI 包:${NC}"
echo -e "   https://pypi.org/project/bento-framework/"
echo ""
echo -e "${GREEN}Workflow 配置:${NC}"
echo -e "   https://github.com/idpxyz/bento/blob/main/.github/workflows/release.yml"
echo ""

# 6. 提示信息
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}💡 提示${NC}"
echo ""
echo -e "如果 GitHub Actions 失败，可能需要："
echo -e "1. 检查 Actions 日志找到错误原因"
echo -e "2. 配置 PYPI_API_TOKEN secret"
echo -e "3. 确保仓库有正确的权限设置"
echo ""
echo -e "重新运行 workflow:"
echo -e "   ${YELLOW}git tag -d v0.1.0${NC}  # 删除本地 tag"
echo -e "   ${YELLOW}git push origin :refs/tags/v0.1.0${NC}  # 删除远程 tag"
echo -e "   ${YELLOW}git tag v0.1.0${NC}  # 重新创建 tag"
echo -e "   ${YELLOW}git push origin v0.1.0${NC}  # 重新推送"
echo ""
