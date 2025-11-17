#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📦 提交策略 - 准备发布${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}检测到的主要更改:${NC}"
echo ""

# 1. CI/CD 相关
echo -e "${GREEN}1️⃣  CI/CD 配置和文档${NC}"
git status -s | grep -E "\.github/|CI_CD|MAKEFILE|RELEASE|check-release|test-ci|FIX_AND"

# 2. 包配置
echo ""
echo -e "${GREEN}2️⃣  包配置和构建${NC}"
git status -s | grep -E "Makefile|pyproject.toml|scripts/release"

# 3. 源代码修改
echo ""
echo -e "${GREEN}3️⃣  源代码修改${NC}"
git status -s | grep -E "src/bento.*\.py$" | head -10

# 4. 测试文件
echo ""
echo -e "${GREEN}4️⃣  测试文件${NC}"
git status -s | grep -E "tests/.*\.py$" | head -5
echo "   ... 更多测试文件"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}建议的提交策略:${NC}"
echo ""
echo "选项 1: 分批提交（推荐）"
echo "  - 更清晰的提交历史"
echo "  - 便于代码审查"
echo ""
echo "选项 2: 一次性提交"
echo "  - 快速发布"
echo "  - 适合个人项目"
echo ""

read -p "选择策略 [1/2]: " -n 1 -r
echo
echo ""

if [[ $REPLY == "1" ]]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}📝 分批提交${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Commit 1: CI/CD
    echo -e "${YELLOW}Commit 1: CI/CD 配置${NC}"
    git add .github/workflows/*.yml \
            CI_CD*.md \
            MAKEFILE*.md \
            RELEASE*.md \
            QUICK_REFERENCE.md \
            check-release.sh \
            test-ci.sh \
            FIX_AND_REDEPLOY.sh \
            COMMIT_STRATEGY.sh 2>/dev/null
    git commit -m "feat: add complete CI/CD pipeline

- Add GitHub Actions workflows (build, release, dependency-review)
- Add automated release process with PyPI publishing
- Add comprehensive testing and deployment guides
- Add monitoring and troubleshooting tools
- Fix changelog generation for first release" 2>/dev/null
    echo -e "${GREEN}✅ CI/CD 配置已提交${NC}"
    echo ""

    # Commit 2: Build system
    echo -e "${YELLOW}Commit 2: 构建系统改进${NC}"
    git add Makefile \
            pyproject.toml \
            scripts/release.sh 2>/dev/null
    git commit -m "feat: improve build and release system

- Update Makefile with auto-detection of Python/pip
- Add Python version check (require 3.12+)
- Add twine auto-installation
- Update coverage requirement to 70%
- Make MyPy non-blocking for release" 2>/dev/null
    echo -e "${GREEN}✅ 构建系统已提交${NC}"
    echo ""

    # Commit 3: CLI improvements
    echo -e "${YELLOW}Commit 3: CLI 工具改进${NC}"
    git add src/bento/toolkit/*.py \
            src/bento/toolkit/*.md \
            src/bento/toolkit/templates/*.tpl 2>/dev/null
    git commit -m "fix: improve CLI tool and templates

- Fix render() function to support Path objects
- Make --context parameter optional with default 'shared'
- Add EventName parameter to templates
- Update templates for modular monolith architecture
- Add comprehensive CLI documentation" 2>/dev/null
    echo -e "${GREEN}✅ CLI 工具已提交${NC}"
    echo ""

    # Commit 4: Tests
    echo -e "${YELLOW}Commit 4: 测试文件${NC}"
    git add tests/unit/infrastructure/test_toolkit*.py \
            tests/unit/persistence/ \
            tests/unit/domain/ 2>/dev/null
    git commit -m "fix: update and add tests

- Fix CLI tests for modular monolith architecture
- Add persistence tests
- Add domain tests
- Update test paths and assertions" 2>/dev/null
    echo -e "${GREEN}✅ 测试文件已提交${NC}"
    echo ""

    # Commit 5: Other changes
    echo -e "${YELLOW}Commit 5: 其他改进${NC}"
    git add -A
    git commit -m "chore: clean up and minor improvements

- Fix import ordering (ruff)
- Remove obsolete files
- Update documentation
- Add packaging guides" 2>/dev/null
    echo -e "${GREEN}✅ 其他改进已提交${NC}"
    echo ""

else
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}📝 一次性提交${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    git add -A
    git commit -m "feat: complete CI/CD setup and improvements

Major changes:
- Add GitHub Actions workflows for build, release, and dependency review
- Improve Makefile with auto-detection and version checks
- Fix CLI tools and templates for modular monolith architecture
- Add comprehensive testing and deployment documentation
- Fix changelog generation for first release
- Update coverage requirements and make MyPy non-blocking
- Add automated release scripts and monitoring tools
- Fix import ordering and clean up codebase

This prepares the project for v0.1.0 release."

    echo -e "${GREEN}✅ 所有更改已提交${NC}"
    echo ""
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📤 推送更改${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "是否推送到远程? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin main || git push origin master
    echo ""
    echo -e "${GREEN}✅ 更改已推送${NC}"
    echo ""

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🏷️  创建和推送 Tag${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 删除旧 tag（如果存在）
    if git tag -l | grep -q "v0.1.0"; then
        git tag -d v0.1.0
        git push origin :refs/tags/v0.1.0 2>/dev/null
        echo -e "${GREEN}✅ 旧 tag 已删除${NC}"
    fi

    # 创建新 tag
    git tag v0.1.0
    echo -e "${GREEN}✅ Tag v0.1.0 已创建${NC}"
    echo ""

    read -p "是否推送 tag 并触发 CI/CD? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin v0.1.0
        echo ""
        echo -e "${GREEN}✅ Tag 已推送！CI/CD 已触发！${NC}"
        echo ""
        echo -e "${YELLOW}📊 监控进度:${NC}"
        echo "   https://github.com/idpxyz/bento/actions"
        echo ""
        echo -e "${YELLOW}🔍 检查状态:${NC}"
        echo "   ./check-release.sh"
        echo ""
    fi
else
    echo ""
    echo -e "${YELLOW}⏸  更改未推送${NC}"
    echo ""
    echo "稍后可以手动推送:"
    echo "  git push"
    echo "  git tag v0.1.0"
    echo "  git push origin v0.1.0"
    echo ""
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 完成！${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
