#!/usr/bin/env python3
"""查询和验证 Outbox 表数据的便捷脚本"""

import json
import sqlite3


def check_outbox():
    """检查 Outbox 表数据"""
    conn = sqlite3.connect("my_shop.db")
    cursor = conn.cursor()

    # 统计
    cursor.execute("SELECT COUNT(*) FROM outbox")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM outbox WHERE payload IS NULL")
    null_count = cursor.fetchone()[0]

    print("=" * 80)
    print("📊 Outbox 表统计")
    print("=" * 80)
    print(f"✅ 总事件数: {total}")
    print(f"❌ Payload 为 NULL: {null_count}")
    print(f"✅ Payload 有效: {total - null_count}")
    print("")

    # 详细列表
    cursor.execute("""
        SELECT id, tenant_id, aggregate_id, type, payload, status, created_at
        FROM outbox
        ORDER BY created_at DESC
    """)

    print("=" * 80)
    print("📋 事件详情")
    print("=" * 80)

    for i, row in enumerate(cursor.fetchall(), 1):
        event_id, tenant_id, agg_id, event_type, payload, status, created_at = row

        print(f"\n{i}. 🔹 Event: {event_type}")
        print(f"   ID: {event_id}")
        print(f"   Tenant: {tenant_id}")
        print(f"   Aggregate: {agg_id or '(none)'}")
        print(f"   Status: {status}")
        print(f"   Created: {created_at}")

        if payload:
            try:
                payload_data = json.loads(payload)
                print("   ✅ Payload (valid JSON):")
                print(f"      {json.dumps(payload_data, indent=6, ensure_ascii=False)}")
            except Exception as e:
                print(f"   ⚠️  Payload (invalid JSON): {e}")
                print(f"      {payload[:200]}...")
        else:
            print("   ❌ Payload: NULL")

    conn.close()


if __name__ == "__main__":
    check_outbox()
