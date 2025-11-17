#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VERSION="0.1.1"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 监控 v${VERSION} 发布进度${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

MAX_ATTEMPTS=60
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))

    echo -e "${YELLOW}检查 #$ATTEMPT (最多检查 $MAX_ATTEMPTS 次)...${NC}"

    # 检查 PyPI
    PYPI_VERSION=$(python3 << 'EOF'
import urllib.request
import json
try:
    url = "https://pypi.org/pypi/bento-framework/json"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
        print(data['info']['version'])
except:
    print("error")
EOF
)

    if [ "$PYPI_VERSION" = "$VERSION" ]; then
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}🎉 v${VERSION} 发布成功！${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${BLUE}📦 PyPI 版本: ${GREEN}${PYPI_VERSION}${NC}"
        echo ""
        echo -e "${YELLOW}✅ 验证安装:${NC}"
        echo "   pip install bento-framework==$VERSION"
        echo ""
        echo -e "${YELLOW}🔗 查看:${NC}"
        echo "   PyPI: https://pypi.org/project/bento-framework/"
        echo "   GitHub: https://github.com/idpxyz/bento/releases/tag/v$VERSION"
        echo ""
        exit 0
    else
        echo "   PyPI 当前版本: $PYPI_VERSION (等待 $VERSION...)"
    fi

    # 每 10 秒检查一次
    if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
        echo "   等待 10 秒后重试..."
        sleep 10
        echo ""
    fi
done

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⏰ 超时${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "CI/CD 可能需要更长时间。请手动检查："
echo "  GitHub Actions: https://github.com/idpxyz/bento/actions"
echo "  PyPI: https://pypi.org/project/bento-framework/"
echo ""
