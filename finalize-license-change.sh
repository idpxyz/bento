#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📦 完成许可证变更 - 准备 v0.2.0${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}步骤 1: 更新版本号到 0.2.0${NC}"
echo ""
sed -i 's/version = "0.1.1"/version = "0.2.0"/' pyproject.toml
echo -e "${GREEN}✅ 版本号已更新：0.1.1 → 0.2.0${NC}"
grep "^version" pyproject.toml
echo ""

echo -e "${YELLOW}步骤 2: 查看所有变更${NC}"
echo ""
git status --short
echo ""

echo -e "${YELLOW}步骤 3: 提交许可证变更${NC}"
echo ""
read -p "是否提交这些变更? [y/N] " -n 1 -r
echo
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add LICENSE LICENSE.PROPRIETARY LICENSE.MIT.backup \
           pyproject.toml pyproject.toml.backup \
           README.md \
           LICENSE_HISTORY.md LICENSE_CHANGE_PLAN.md \
           change-license.sh finalize-license-change.sh

    git commit -m "chore: change license from MIT to idp.xyz Proprietary and bump to v0.2.0

BREAKING CHANGE: License change from MIT to Proprietary

Changes:
- Replace LICENSE with idp.xyz Proprietary License
- Update pyproject.toml license field to 'Proprietary'
- Bump version from 0.1.1 to 0.2.0
- Add license information to README.md
- Create LICENSE_HISTORY.md to document version-specific licenses
- Backup original MIT license as LICENSE.MIT.backup

Important Notes:
- This change affects v0.2.0 and later versions only
- Previous versions (v0.1.x) remain under MIT License permanently
- v0.1.x users retain all MIT License rights indefinitely

License Terms:
- Proprietary software owned by idp.xyz
- Commercial use requires separate license
- No redistribution without permission
- Contact: licensing@idp.xyz

Migration Path:
- Users on v0.1.x can continue using under MIT
- Upgrading to v0.2.0+ requires accepting new Proprietary License
- Commercial licenses available upon request"

    echo ""
    echo -e "${GREEN}✅ 变更已提交${NC}"
    echo ""

    read -p "是否推送到远程仓库? [y/N] " -n 1 -r
    echo
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BRANCH=$(git branch --show-current)
        git push origin $BRANCH
        echo ""
        echo -e "${GREEN}✅ 已推送到远程分支: $BRANCH${NC}"
    else
        echo -e "${YELLOW}⏸  未推送，稍后可手动推送：git push${NC}"
    fi
else
    echo -e "${YELLOW}⏸  未提交${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 许可证变更完成！${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}📋 许可证版本映射:${NC}"
echo ""
echo "  v0.1.0a2, v0.1.1  →  MIT License (永久)"
echo "  v0.2.0 及以后     →  idp.xyz Proprietary License"
echo ""

echo -e "${YELLOW}🔒 后续建议:${NC}"
echo ""
echo "1. 【GitHub仓库】考虑转为私有："
echo "   Settings → General → Danger Zone → Change visibility → Private"
echo ""
echo "2. 【PyPI管理】选择分发策略："
echo "   A) 继续使用 PyPI (公开但有许可证限制)"
echo "   B) 使用私有 PyPI (Gemfury, JFrog, AWS CodeArtifact)"
echo "   C) 直接分发 (仅授权用户)"
echo ""
echo "3. 【v0.2.0发布】创建 Release Notes 时明确说明许可证变更"
echo ""
echo "4. 【访问控制】设置授权机制（如果需要）"
echo ""

echo -e "${YELLOW}📞 商业授权联系:${NC}"
echo "   Email: licensing@idp.xyz"
echo ""

echo -e "${YELLOW}📚 相关文档:${NC}"
echo "   • LICENSE - 新的私有许可证"
echo "   • LICENSE_HISTORY.md - 许可证变更历史"
echo "   • LICENSE_CHANGE_PLAN.md - 完整变更计划"
echo ""
