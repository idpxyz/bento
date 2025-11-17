#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📜 许可证变更：MIT → idp.xyz Proprietary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}⚠️  重要提示：${NC}"
echo ""
echo "1. 已发布的版本 (v0.1.x) 在 MIT License 下发布"
echo "2. MIT License 是不可撤销的"
echo "3. 此变更仅影响未来版本 (v0.2.0+)"
echo ""
echo -e "${YELLOW}这意味着：${NC}"
echo "  • v0.1.1 及更早版本永久保持 MIT License"
echo "  • 已下载用户保留 MIT 权利"
echo "  • 新版本将使用 idp.xyz Proprietary License"
echo ""

read -p "是否继续许可证变更? [y/N] " -n 1 -r
echo
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}1️⃣  备份当前 LICENSE${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f LICENSE ]; then
    cp LICENSE LICENSE.MIT.backup
    echo -e "${GREEN}✅ 已备份到 LICENSE.MIT.backup${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 LICENSE 文件${NC}"
fi
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}2️⃣  应用新许可证${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f LICENSE.PROPRIETARY ]; then
    cp LICENSE.PROPRIETARY LICENSE
    echo -e "${GREEN}✅ 已应用 idp.xyz Proprietary License${NC}"
else
    echo -e "${RED}❌ 未找到 LICENSE.PROPRIETARY 文件${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}3️⃣  更新 pyproject.toml${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f pyproject.toml ]; then
    # 备份
    cp pyproject.toml pyproject.toml.backup

    # 更新许可证字段
    sed -i 's/license = { text = "MIT" }/license = { text = "Proprietary" }/' pyproject.toml

    # 验证
    if grep -q 'license = { text = "Proprietary" }' pyproject.toml; then
        echo -e "${GREEN}✅ pyproject.toml 已更新${NC}"
        echo "   更改: MIT → Proprietary"
    else
        echo -e "${RED}❌ pyproject.toml 更新失败${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ 未找到 pyproject.toml 文件${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}4️⃣  更新 README.md${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f README.md ]; then
    # 检查是否已有 License 章节
    if grep -q "## License" README.md; then
        echo "  README.md 中已有 License 章节"
        echo "  请手动更新许可证信息"
    else
        # 添加 License 章节（在文件末尾）
        cat >> README.md << 'EOFREADME'

## License

**Version 0.2.0 and later:**

Copyright © 2025 idp.xyz. All Rights Reserved.

This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use of this software is strictly prohibited.

For licensing inquiries, please contact: licensing@idp.xyz

**Previous versions (v0.1.x):**

Licensed under MIT License.
EOFREADME
        echo -e "${GREEN}✅ README.md 已添加许可证信息${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未找到 README.md 文件${NC}"
fi
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}5️⃣  创建版本历史文档${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cat > LICENSE_HISTORY.md << 'EOFLICENSE'
# License History

## Version Timeline

### v0.2.0 and later
**License**: idp.xyz Proprietary License
**Effective**: 2025-11-17
**Status**: Closed source, proprietary

See [LICENSE](LICENSE) for full terms.

### v0.1.x (0.1.0a2, 0.1.1)
**License**: MIT License
**Published**: 2025-11-17
**Status**: Open source (permanently)

These versions were published under MIT License on PyPI and remain under
that license indefinitely. Anyone who downloaded these versions retains
the rights granted by the MIT License.

## Important Notes

1. **MIT License is irrevocable**: Versions released under MIT License
   cannot be relicensed retroactively.

2. **Dual availability**: If you need v0.1.x, you can still use them
   under MIT License from PyPI.

3. **Upgrade path**: Upgrading from v0.1.x to v0.2.0+ means accepting
   the new proprietary license.

## License Terms

### For v0.2.0+
- Proprietary software
- Commercial use requires license
- No redistribution without permission
- Contact: licensing@idp.xyz

### For v0.1.x
- MIT License terms apply
- Free to use, modify, distribute
- See LICENSE.MIT.backup for full text

## Questions?

For licensing questions or commercial licensing inquiries:
- Email: licensing@idp.xyz
- Website: https://idp.xyz
EOFLICENSE

echo -e "${GREEN}✅ 已创建 LICENSE_HISTORY.md${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}6️⃣  变更摘要${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}已修改的文件:${NC}"
echo "  • LICENSE (MIT → Proprietary)"
echo "  • pyproject.toml (许可证字段)"
echo "  • README.md (添加许可证说明)"
echo ""

echo -e "${YELLOW}已创建的文件:${NC}"
echo "  • LICENSE.MIT.backup (原 MIT License 备份)"
echo "  • LICENSE_HISTORY.md (许可证变更历史)"
echo "  • pyproject.toml.backup (备份)"
echo ""

echo -e "${YELLOW}Git 状态:${NC}"
git status --short
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}7️⃣  提交变更${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "是否提交这些变更到 Git? [y/N] " -n 1 -r
echo
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add LICENSE LICENSE.PROPRIETARY LICENSE.MIT.backup \
           pyproject.toml README.md LICENSE_HISTORY.md \
           LICENSE_CHANGE_PLAN.md

    git commit -m "chore: change license from MIT to idp.xyz Proprietary

BREAKING CHANGE: License change from MIT to Proprietary

- Replace LICENSE with idp.xyz Proprietary License
- Update pyproject.toml license field
- Add license information to README.md
- Create LICENSE_HISTORY.md to document the change

Important: This change affects v0.2.0 and later versions only.
Previous versions (v0.1.x) remain under MIT License permanently."

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
    echo -e "${YELLOW}⏸  未提交，请手动检查并提交：${NC}"
    echo "  git add LICENSE pyproject.toml README.md ..."
    echo "  git commit -m 'chore: change license to proprietary'"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 许可证变更完成！${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}📋 后续步骤：${NC}"
echo ""
echo "1. 【重要】更新 v0.2.0 的版本号："
echo "   sed -i 's/version = \"0.1.1\"/version = \"0.2.0\"/' pyproject.toml"
echo ""
echo "2. 在 Release Notes 中明确说明许可证变更"
echo ""
echo "3. 考虑以下选项："
echo "   • GitHub 仓库转为私有"
echo "   • 使用私有 PyPI 服务器"
echo "   • 设置访问控制"
echo ""
echo "4. 查看完整计划："
echo "   cat LICENSE_CHANGE_PLAN.md"
echo ""
echo "5. 查看许可证历史："
echo "   cat LICENSE_HISTORY.md"
echo ""

echo -e "${YELLOW}⚠️  记住：${NC}"
echo "  v0.1.x 版本永久保持 MIT License（无法更改）"
echo ""
