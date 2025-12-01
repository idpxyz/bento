# Bento Framework Outbox 生产部署指南

## 🚀 概述

本指南提供了Bento Framework Outbox和MessageBus系统在生产环境中的完整部署方案，包括性能优化、安全配置、监控设置和最佳实践。

## 📋 部署检查清单

### ✅ 环境准备
- [ ] PostgreSQL 12+ 数据库
- [ ] Python 3.11+ 运行环境
- [ ] Redis/Pulsar消息队列
- [ ] 监控系统 (可选)

### ✅ 配置优化
- [ ] 数据库连接池配置
- [ ] OutboxProjector性能参数
- [ ] 索引创建和优化
- [ ] 环境变量设置

### ✅ 安全配置
- [ ] 数据库连接安全
- [ ] 事件序列化安全
- [ ] 网络安全配置

### ✅ 监控设置
- [ ] 性能指标监控
- [ ] 告警阈值设置
- [ ] 日志配置

## 🗄️ 数据库配置

### PostgreSQL生产配置

```sql
-- 1. 创建Outbox表 (已包含优化索引)
CREATE TABLE outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(128) NOT NULL,
    aggregate_id VARCHAR(128),
    aggregate_type VARCHAR(100),
    topic VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    schema_id VARCHAR(128),
    schema_version INTEGER DEFAULT 1,
    payload JSONB NOT NULL,
    event_metadata JSONB DEFAULT '{}',
    status VARCHAR(10) DEFAULT 'NEW',
    retry_count INTEGER DEFAULT 0,
    retry_after TIMESTAMP WITH TIME ZONE,
    error_message VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 性能优化索引
CREATE INDEX ix_tenant_id_status ON outbox(tenant_id, status);
CREATE INDEX ix_outbox_processing ON outbox(status, retry_after);
CREATE INDEX ix_outbox_topic ON outbox(topic);
CREATE INDEX ix_outbox_aggregate ON outbox(aggregate_type, aggregate_id);

-- P2-B 性能优化索引
CREATE INDEX ix_outbox_cleanup ON outbox(tenant_id, created_at);
CREATE INDEX ix_outbox_query_opt ON outbox(status, retry_after, tenant_id);
CREATE INDEX ix_outbox_tenant_created ON outbox(tenant_id, created_at, status);
CREATE INDEX ix_outbox_processing_tenant ON outbox(tenant_id, status, retry_count);
```

### 连接池配置

```python
# production_db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

def create_production_engine(database_url: str):
    """生产环境数据库引擎配置"""
    return create_async_engine(
        database_url,
        # 连接池配置
        pool_size=20,              # 基础连接池大小
        max_overflow=10,           # 允许溢出连接数
        pool_pre_ping=True,        # 连接验证
        pool_recycle=3600,         # 1小时回收连接

        # 性能配置
        echo=False,                # 生产环境关闭SQL日志
        future=True,               # 使用SQLAlchemy 2.0 API

        # 超时配置
        connect_args={
            "command_timeout": 60,
            "server_settings": {
                "jit": "off",  # 关闭JIT以获得稳定性能
            }
        }
    )

# 使用示例
DATABASE_URL = "postgresql+asyncpg://user:password@host:5432/database"
engine = create_production_engine(DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

## ⚙️ OutboxProjector生产配置

### 高性能配置

```python
# config/production.py
from bento.config.outbox import OutboxProjectorConfig

# 高吞吐量配置
HIGH_THROUGHPUT_CONFIG = OutboxProjectorConfig(
    # 核心性能参数
    batch_size=1000,                    # 大批量处理
    max_concurrent_projectors=8,        # 多并发处理

    # 轮询策略
    sleep_busy=0.05,                    # 5ms快速轮询
    sleep_idle=0.5,                     # 500ms空闲轮询
    sleep_idle_max=5.0,                 # 最大5s空闲

    # 重试策略
    max_retry_attempts=5,               # 最大重试5次
    error_retry_delay=2.0,              # 2s重试间隔

    # 性能监控
    enable_performance_monitoring=True, # 启用监控

    # 数据库优化
    connection_pool_size=20,            # 连接池大小
    query_timeout_seconds=30,           # 查询超时
    batch_commit_size=2000,             # 批量提交

    # 多租户
    default_tenant_id="production"
)

# 低延迟配置 (适合实时场景)
LOW_LATENCY_CONFIG = OutboxProjectorConfig(
    batch_size=100,                     # 小批量快速处理
    max_concurrent_projectors=15,       # 高并发
    sleep_busy=0.01,                    # 10ms极速轮询
    sleep_idle=0.1,                     # 100ms快速响应
    max_retry_attempts=3,               # 快速失败
    enable_performance_monitoring=True
)
```

### 环境变量配置

```bash
# .env.production
# 数据库配置
DATABASE_URL=postgresql+asyncpg://outbox_user:secure_password@db-host:5432/outbox_db

# Outbox配置
BENTO_OUTBOX_BATCH_SIZE=1000
BENTO_OUTBOX_MAX_CONCURRENT_PROJECTORS=8
BENTO_OUTBOX_SLEEP_BUSY=0.05
BENTO_OUTBOX_SLEEP_IDLE=0.5
BENTO_OUTBOX_MAX_RETRY_ATTEMPTS=5
BENTO_OUTBOX_ENABLE_PERFORMANCE_MONITORING=true

# 消息队列配置
PULSAR_SERVICE_URL=pulsar://pulsar-cluster:6650
REDIS_URL=redis://redis-cluster:6379

# 监控配置
METRICS_PORT=9090
LOG_LEVEL=INFO

# 安全配置
ENCRYPTION_KEY=your-32-byte-encryption-key
```

## 📊 性能监控配置

### 监控设置

```python
# monitoring/setup.py
from bento.infrastructure.monitoring.performance import PerformanceMonitor
import asyncio
import logging

async def setup_monitoring(session_factory, projector):
    """设置生产环境监控"""

    # 1. 性能监控
    monitor = PerformanceMonitor(session_factory)

    # 2. 定期健康检查
    async def health_check():
        while True:
            try:
                # 获取性能指标
                metrics = await monitor.get_metrics()

                # 分析瓶颈
                analysis = await monitor.analyze_performance_bottlenecks()

                # 记录关键指标
                logging.info(
                    f"Outbox Performance - "
                    f"Pending: {metrics.pending_events}, "
                    f"EPS: {metrics.events_per_second:.2f}, "
                    f"Query Time: {metrics.avg_query_time_ms:.2f}ms"
                )

                # 高严重性告警
                if analysis['severity'] in ['high', 'critical']:
                    logging.error(f"Performance Alert: {analysis['bottlenecks']}")

                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logging.error(f"Health check failed: {e}")
                await asyncio.sleep(60)

    # 启动后台监控
    asyncio.create_task(health_check())
    return monitor
```

### 告警配置

```python
# monitoring/alerts.py
PERFORMANCE_THRESHOLDS = {
    'pending_events_critical': 50000,      # 5万事件积压
    'pending_events_warning': 10000,       # 1万事件积压
    'avg_query_time_critical': 1000,       # 1秒查询时间
    'avg_query_time_warning': 500,         # 500ms查询时间
    'events_per_second_min': 100,          # 最小处理速率
    'connection_pool_usage_critical': 0.9, # 90%连接池使用率
}

async def check_alerts(metrics):
    """检查告警条件"""
    alerts = []

    if metrics.pending_events > PERFORMANCE_THRESHOLDS['pending_events_critical']:
        alerts.append({
            'level': 'CRITICAL',
            'message': f'Large event backlog: {metrics.pending_events} events',
            'action': 'Increase projector instances or batch size'
        })

    if metrics.avg_query_time_ms > PERFORMANCE_THRESHOLDS['avg_query_time_critical']:
        alerts.append({
            'level': 'CRITICAL',
            'message': f'Slow queries: {metrics.avg_query_time_ms:.2f}ms average',
            'action': 'Check database performance and indexes'
        })

    return alerts
```

## 🧹 运维任务

### 历史数据清理

```python
# maintenance/cleanup.py
from bento.infrastructure.monitoring.performance import cleanup_old_outbox_records
import asyncio

async def schedule_cleanup(session_factory):
    """定期清理历史数据"""

    while True:
        try:
            # 保留7天数据，每天清理一次
            stats = await cleanup_old_outbox_records(
                session_factory,
                retention_days=7,
                batch_size=5000,
                dry_run=False  # 实际执行
            )

            logging.info(
                f"Cleanup completed - "
                f"Deleted: {stats['deleted']} records in {stats['batches']} batches"
            )

            # 每天凌晨2点执行
            await asyncio.sleep(24 * 3600)

        except Exception as e:
            logging.error(f"Cleanup failed: {e}")
            await asyncio.sleep(3600)  # 1小时后重试
```

### 部署脚本

```bash
#!/bin/bash
# deploy.sh - 生产部署脚本

set -e

echo "🚀 Deploying Bento Outbox to Production"

# 1. 环境检查
echo "📋 Environment Check..."
python -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
psql $DATABASE_URL -c "SELECT version();" > /dev/null

# 2. 数据库迁移
echo "🗄️ Database Migration..."
python -m alembic upgrade head

# 3. 索引检查和创建
echo "📊 Database Optimization..."
python scripts/create_indexes.py

# 4. 配置验证
echo "⚙️ Configuration Validation..."
python -c "
from bento.config.validation import validate_config
from bento.config.outbox import get_outbox_projector_config

config = get_outbox_projector_config()
result = validate_config(config)
assert result.is_valid, f'Config validation failed: {result.errors}'
print('✅ Configuration is valid')
"

# 5. 启动服务
echo "🚀 Starting Services..."
python -m gunicorn app:app --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 --bind 0.0.0.0:8000 &

python -m bento.infrastructure.projection.projector_service &

echo "✅ Deployment completed successfully!"
```

## 🔒 安全最佳实践

### 数据库安全

```python
# security/database.py
import os
from cryptography.fernet import Fernet

# 1. 敏感数据加密
def encrypt_sensitive_payload(payload: dict) -> dict:
    """加密敏感事件数据"""
    cipher = Fernet(os.environ['ENCRYPTION_KEY'].encode())

    sensitive_fields = ['password', 'token', 'secret', 'key']
    encrypted_payload = payload.copy()

    for field in sensitive_fields:
        if field in encrypted_payload:
            encrypted_payload[field] = cipher.encrypt(
                str(encrypted_payload[field]).encode()
            ).decode()

    return encrypted_payload

# 2. 连接安全
DATABASE_CONFIG = {
    'sslmode': 'require',           # 强制SSL
    'sslcert': '/path/to/client.crt',
    'sslkey': '/path/to/client.key',
    'sslrootcert': '/path/to/ca.crt'
}
```

### 网络安全

```yaml
# docker-compose.production.yml
version: '3.8'
services:
  outbox-projector:
    image: bento-outbox:latest
    networks:
      - internal
    environment:
      - DATABASE_URL=postgresql://...
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

networks:
  internal:
    driver: overlay
    internal: true  # 内部网络，不暴露到外部
```

## 📈 性能基准和容量规划

### 性能基准

```python
# benchmarks/performance_test.py
async def performance_benchmark():
    """性能基准测试"""

    test_scenarios = [
        {'batch_size': 100, 'concurrent': 1, 'expected_tps': 1000},
        {'batch_size': 500, 'concurrent': 5, 'expected_tps': 5000},
        {'batch_size': 1000, 'concurrent': 10, 'expected_tps': 10000}
    ]

    for scenario in test_scenarios:
        print(f"Testing: {scenario}")
        # 执行性能测试...
        actual_tps = await run_performance_test(scenario)

        if actual_tps >= scenario['expected_tps']:
            print(f"✅ PASS - {actual_tps} TPS")
        else:
            print(f"❌ FAIL - {actual_tps} TPS (expected {scenario['expected_tps']})")
```

### 容量规划

| 场景 | 事件量/天 | 推荐配置 | 资源需求 |
|------|-----------|----------|----------|
| **小型** | 10万 | batch_size=200, concurrent=2 | 2 CPU, 4GB RAM |
| **中型** | 100万 | batch_size=500, concurrent=5 | 4 CPU, 8GB RAM |
| **大型** | 1000万 | batch_size=1000, concurrent=10 | 8 CPU, 16GB RAM |
| **超大型** | 1亿+ | batch_size=2000, concurrent=20 | 16 CPU, 32GB RAM |

## 🚨 故障排查指南

### 常见问题

1. **事件积压**
   - 检查: `SELECT COUNT(*) FROM outbox WHERE status='NEW'`
   - 解决: 增加batch_size或concurrent_projectors

2. **查询缓慢**
   - 检查: 索引使用情况
   - 解决: 重建索引，优化查询

3. **连接池耗尽**
   - 检查: 连接池使用率
   - 解决: 增加pool_size或优化轮询频率

### 诊断脚本

```python
# scripts/diagnose.py
async def diagnose_outbox_health(session_factory):
    """Outbox系统健康诊断"""

    print("🔍 Outbox Health Diagnosis")
    print("=" * 30)

    async with session_factory() as session:
        # 1. 事件状态分布
        result = await session.execute(
            text("SELECT status, COUNT(*) FROM outbox GROUP BY status")
        )
        print("📊 Event Status Distribution:")
        for row in result:
            print(f"   {row.status}: {row.count}")

        # 2. 积压分析
        result = await session.execute(
            text("SELECT COUNT(*) FROM outbox WHERE created_at < NOW() - INTERVAL '1 hour'")
        )
        old_events = result.scalar()
        print(f"⏰ Events older than 1 hour: {old_events}")

        # 3. 失败分析
        result = await session.execute(
            text("SELECT error_message, COUNT(*) FROM outbox WHERE status='FAILED' GROUP BY error_message LIMIT 10")
        )
        print("❌ Top failure reasons:")
        for row in result:
            print(f"   {row.error_message}: {row.count}")
```

## 🎯 总结

这份生产部署指南涵盖了Bento Framework Outbox系统在生产环境中的各个方面：

✅ **完整的配置方案** - 数据库、连接池、性能参数
✅ **监控和告警** - 实时指标、健康检查、问题预警
✅ **安全最佳实践** - 数据加密、网络安全、访问控制
✅ **运维自动化** - 部署脚本、清理任务、诊断工具
✅ **性能调优** - 基准测试、容量规划、故障排查

**🚀 现在你拥有了一个完全生产就绪的企业级Outbox解决方案！**
