#!/usr/bin/env bash
# Bento Framework 发布脚本
set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：打印带颜色的消息
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# 函数：检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        # twine 可以自动安装，其他命令报错
        if [ "$1" = "twine" ]; then
            warning "$1 未安装，正在自动安装..."
            install_twine
            return 0
        else
            error "$1 未安装，请先安装: pip install $1"
        fi
    fi
}

# 函数：自动安装 twine
install_twine() {
    if command -v uv >/dev/null 2>&1; then
        # 使用 uv pip
        uv pip install twine -q 2>/dev/null || uv pip install twine
    elif [ -f .venv/bin/python3 ]; then
        # 使用虚拟环境
        .venv/bin/python3 -m pip install twine -q 2>/dev/null || \
        .venv/bin/python3 -m pip install twine
    elif [ -f .venv/bin/python ]; then
        .venv/bin/python -m pip install twine -q 2>/dev/null || \
        .venv/bin/python -m pip install twine
    else
        # 使用系统 pip
        pip3 install twine -q 2>/dev/null || pip3 install twine
    fi
    success "twine 安装完成"
}

# 函数：获取当前版本
get_current_version() {
    grep -E '^version = ' pyproject.toml | cut -d'"' -f2
}

# 函数：检查 git 状态
check_git_status() {
    if [[ -n $(git status -s) ]]; then
        warning "工作目录有未提交的更改"
        git status -s
        read -p "是否继续? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "已取消发布"
        fi
    fi
}

# 函数：运行测试
run_tests() {
    info "运行测试..."
    if ! pytest --cov --cov-fail-under=80; then
        error "测试失败或覆盖率不足 80%"
    fi
    success "测试通过"
}

# 函数：代码检查
run_linters() {
    info "运行代码检查..."
    ruff check src/ || error "Ruff 检查失败"
    mypy src/bento || error "MyPy 检查失败"
    success "代码检查通过"
}

# 函数：清理旧文件
clean_build() {
    info "清理构建文件..."
    rm -rf build/ dist/ *.egg-info
    success "清理完成"
}

# 函数：构建包
build_package() {
    info "构建包..."
    python3 -m build || error "构建失败"
    success "构建完成"
}

# 函数：检查包
check_package() {
    info "检查包..."
    twine check dist/* || error "包检查失败"
    success "包检查通过"
}

# 函数：发布到 Test PyPI
publish_test() {
    info "发布到 Test PyPI..."
    twine upload --repository testpypi dist/*
    success "发布到 Test PyPI 完成"
    echo ""
    info "测试安装命令:"
    echo "pip install --index-url https://test.pypi.org/simple/ bento-framework"
}

# 函数：发布到 PyPI
publish_pypi() {
    info "发布到 PyPI..."
    read -p "⚠️  确认发布到 PyPI? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "已取消发布"
    fi
    twine upload dist/*
    success "发布到 PyPI 完成"
    echo ""
    info "安装命令:"
    echo "pip install bento-framework"
}

# 函数：创建 git tag
create_tag() {
    local version=$1
    info "创建 git tag v${version}..."
    git tag -a "v${version}" -m "Release v${version}"
    success "Tag 创建完成: v${version}"
    echo ""
    info "推送 tag 命令:"
    echo "git push origin v${version}"
}

# 主函数
main() {
    echo "🍱 Bento Framework 发布脚本"
    echo "========================================"
    echo ""

    # 检查必要的命令
    check_command python3
    check_command git
    check_command twine
    check_command pytest
    check_command ruff
    check_command mypy

    # 获取当前版本
    CURRENT_VERSION=$(get_current_version)
    info "当前版本: ${CURRENT_VERSION}"
    echo ""

    # 解析参数
    RELEASE_TYPE=${1:-"test"}  # test, prod, tag

    case $RELEASE_TYPE in
        test)
            info "发布模式: Test PyPI"
            check_git_status
            run_tests
            run_linters
            clean_build
            build_package
            check_package
            publish_test
            ;;

        prod)
            info "发布模式: PyPI (生产)"
            check_git_status
            run_tests
            run_linters
            clean_build
            build_package
            check_package
            publish_pypi
            ;;

        tag)
            info "发布模式: 创建 Tag"
            check_git_status
            run_tests
            run_linters
            clean_build
            build_package
            check_package
            create_tag ${CURRENT_VERSION}
            warning "请手动推送 tag: git push origin v${CURRENT_VERSION}"
            warning "GitHub Actions 将自动发布到 PyPI"
            ;;

        dry-run)
            info "发布模式: 干运行（不发布）"
            run_tests
            run_linters
            clean_build
            build_package
            check_package
            success "干运行完成，包已准备好但未发布"
            ;;

        *)
            echo "用法: $0 [test|prod|tag|dry-run]"
            echo ""
            echo "模式:"
            echo "  test     - 发布到 Test PyPI（默认）"
            echo "  prod     - 发布到 PyPI（生产）"
            echo "  tag      - 创建 git tag（触发 CI/CD）"
            echo "  dry-run  - 只构建和检查，不发布"
            echo ""
            exit 1
            ;;
    esac

    echo ""
    success "🎉 发布流程完成！"
}

# 运行主函数
main "$@"
