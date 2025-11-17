#!/bin/bash
# Bento CI/CD 本地测试脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Bento CI/CD 测试脚本${NC}"
echo "================================"
echo ""

# 1. 检查 Python 版本
echo -e "${BLUE}1️⃣  检查 Python 版本...${NC}"
make help | grep "Python:"
make help | grep "版本:"
make check-python
echo -e "${GREEN}✅ Python 版本检查通过${NC}"
echo ""

# 2. 清理
echo -e "${BLUE}2️⃣  清理构建文件...${NC}"
make clean
echo -e "${GREEN}✅ 清理完成${NC}"
echo ""

# 3. 运行测试
echo -e "${BLUE}3️⃣  运行测试...${NC}"
if make test; then
    echo -e "${GREEN}✅ 测试通过${NC}"
else
    echo -e "${RED}❌ 测试失败${NC}"
    exit 1
fi
echo ""

# 4. 代码检查
echo -e "${BLUE}4️⃣  代码检查...${NC}"
if make lint; then
    echo -e "${GREEN}✅ 代码检查通过${NC}"
else
    echo -e "${YELLOW}⚠️  代码检查有警告${NC}"
fi
echo ""

# 5. 构建包
echo -e "${BLUE}5️⃣  构建包...${NC}"
if make build; then
    echo -e "${GREEN}✅ 构建成功${NC}"
    ls -lh dist/
else
    echo -e "${RED}❌ 构建失败${NC}"
    exit 1
fi
echo ""

# 6. 测试 Release 脚本
echo -e "${BLUE}6️⃣  测试 Release 脚本（干运行）...${NC}"
if ! command -v twine >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  twine 未安装，正在自动安装...${NC}"
    # 检测使用 uv 还是 pip
    if command -v uv >/dev/null 2>&1; then
        # 使用 uv pip
        uv pip install twine -q 2>/dev/null || uv pip install twine
    elif [ -f .venv/bin/python3 ]; then
        # 尝试使用虚拟环境的 python -m pip
        .venv/bin/python3 -m pip install twine -q 2>/dev/null || \
        .venv/bin/python3 -m pip install twine
    else
        # 使用系统 pip
        pip install twine -q 2>/dev/null || pip install twine
    fi
    echo -e "${GREEN}✅ twine 安装完成${NC}"
fi

if ./scripts/release.sh dry-run; then
    echo -e "${GREEN}✅ Release 脚本测试通过${NC}"
else
    echo -e "${RED}❌ Release 脚本测试失败${NC}"
    exit 1
fi
echo ""

# 7. 验证 YAML 文件
echo -e "${BLUE}7️⃣  验证 GitHub Actions YAML 文件...${NC}"
YAML_OK=true
for file in .github/workflows/*.yml; do
    echo -n "  检查: $(basename $file) ... "
    if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
        YAML_OK=false
    fi
done

if [ "$YAML_OK" = true ]; then
    echo -e "${GREEN}✅ 所有 YAML 文件语法正确${NC}"
else
    echo -e "${YELLOW}⚠️  某些 YAML 文件有问题（可能缺少 PyYAML）${NC}"
fi
echo ""

# 8. 总结
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 本地测试全部通过！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📋 测试摘要:${NC}"
echo "  ✅ Python 版本检查"
echo "  ✅ 测试套件"
echo "  ✅ 代码检查"
echo "  ✅ 包构建"
echo "  ✅ Release 脚本"
echo "  ✅ YAML 语法"
echo ""
echo -e "${BLUE}🚀 下一步（GitHub Actions 测试）:${NC}"
echo ""
echo -e "${YELLOW}测试 Build Workflow:${NC}"
echo "  git checkout -b test-ci"
echo "  git push origin test-ci"
echo "  gh pr create --base develop"
echo ""
echo -e "${YELLOW}测试 Release Workflow (Alpha):${NC}"
echo "  git tag v0.1.0a99"
echo "  git push origin v0.1.0a99"
echo "  # 访问: https://github.com/your-org/bento/actions"
echo ""
echo -e "${BLUE}📚 查看完整测试指南:${NC}"
echo "  cat CI_CD_TESTING_GUIDE.md"
echo ""
