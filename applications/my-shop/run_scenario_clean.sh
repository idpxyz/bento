#!/bin/bash
# 运行场景前清理 Outbox

cd /workspace/bento/applications/my-shop

echo "清理 Outbox 表中的未处理事件..."
sqlite3 my_shop.db "DELETE FROM outbox WHERE status IN ('NEW', 'ERR'); SELECT 'Deleted ' || changes() || ' events';"

echo ""
echo "运行场景..."
cd /workspace/bento
uv run python applications/my-shop/scenario_complete_shopping_flow.py
