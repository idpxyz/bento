"""OutboxProjector 使用示例 - 展示配置外部化后的新API

这个示例展示了如何使用配置外部化后的 OutboxProjector，
包括不同的配置方式和性能调优场景。
"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# 添加项目路径
sys.path.insert(0, '/workspace/bento/src')

from bento.infrastructure.projection.projector import OutboxProjector
from bento.adapters.messaging.inprocess.message_bus import InProcessMessageBus
from bento.config.outbox import OutboxProjectorConfig
from bento.config.templates import ConfigTemplates


async def basic_usage_example():
    """基础使用示例 - 使用默认配置"""
    print("📋 1. 基础使用（默认配置）")

    # 创建基础组件
    engine = create_async_engine("sqlite+aiosqlite:///memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    message_bus = InProcessMessageBus()

    # 使用默认配置（从环境变量加载）
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=message_bus,
        tenant_id="basic_tenant"
        # config 参数省略，将从环境变量加载默认配置
    )

    print(f"   • 创建投影器成功，租户: {projector._tenant_id}")
    print(f"   • 批量大小: {projector._config.batch_size}")
    print(f"   • 最大重试: {projector._config.max_retry_attempts}")

    await engine.dispose()


async def custom_config_example():
    """自定义配置示例"""
    print("\n⚙️ 2. 自定义配置")

    # 创建自定义配置
    custom_config = OutboxProjectorConfig(
        batch_size=500,
        max_retry_attempts=15,
        sleep_busy=0.05,
        sleep_idle=2.0,
        default_tenant_id="custom_tenant"
    )

    engine = create_async_engine("sqlite+aiosqlite:///memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    message_bus = InProcessMessageBus()

    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=message_bus,
        config=custom_config
    )

    print(f"   • 自定义批量大小: {projector._config.batch_size}")
    print(f"   • 自定义重试次数: {projector._config.max_retry_attempts}")
    print(f"   • 自定义轮询间隔: {projector._config.sleep_busy}s")

    await engine.dispose()


async def template_config_example():
    """配置模板使用示例"""
    print("\n🎨 3. 配置模板使用")

    # 不同环境的配置模板
    scenarios = [
        ("开发环境", "development"),
        ("生产环境", "production"),
        ("高吞吐量", "high_throughput"),
        ("低延迟", "low_latency")
    ]

    for scenario_name, template_name in scenarios:
        config = ConfigTemplates.get_template(template_name)

        print(f"   • {scenario_name}:")
        print(f"     批量: {config.batch_size}, 重试: {config.max_retry_attempts}")
        print(f"     轮询: {config.sleep_busy}s, 租户: {config.default_tenant_id}")


async def environment_config_example():
    """环境变量配置示例"""
    print("\n🌍 4. 环境变量配置")

    # 设置环境变量
    os.environ["BENTO_OUTBOX_BATCH_SIZE"] = "1000"
    os.environ["BENTO_OUTBOX_MAX_RETRY_ATTEMPTS"] = "8"
    os.environ["BENTO_OUTBOX_SLEEP_BUSY"] = "0.02"
    os.environ["BENTO_OUTBOX_DEFAULT_TENANT_ID"] = "env_tenant"

    # 从环境变量创建配置
    env_config = OutboxProjectorConfig.from_env()

    print(f"   • 环境变量配置:")
    print(f"     批量大小: {env_config.batch_size}")
    print(f"     最大重试: {env_config.max_retry_attempts}")
    print(f"     轮询间隔: {env_config.sleep_busy}s")
    print(f"     租户ID: {env_config.default_tenant_id}")

    engine = create_async_engine("sqlite+aiosqlite:///memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    message_bus = InProcessMessageBus()

    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=message_bus,
        config=env_config
    )

    print(f"   • 投影器使用环境配置成功")

    await engine.dispose()


async def multi_tenant_example():
    """多租户场景示例"""
    print("\n🏢 5. 多租户场景")

    engine = create_async_engine("sqlite+aiosqlite:///memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    message_bus = InProcessMessageBus()

    # 为不同租户创建不同配置的投影器
    tenants = [
        {
            "tenant_id": "tenant_a",
            "config": ConfigTemplates.get_template("production")
        },
        {
            "tenant_id": "tenant_b",
            "config": OutboxProjectorConfig(
                batch_size=200,
                max_retry_attempts=5,
                default_tenant_id="tenant_b"
            )
        },
        {
            "tenant_id": "tenant_c",
            "config": ConfigTemplates.get_template("high_throughput")
        }
    ]

    projectors = []

    for tenant in tenants:
        projector = OutboxProjector(
            session_factory=session_factory,
            message_bus=message_bus,
            tenant_id=tenant["tenant_id"],
            config=tenant["config"]
        )
        projectors.append(projector)

        print(f"   • {tenant['tenant_id']}: 批量={projector._config.batch_size}")

    print(f"   • 创建 {len(projectors)} 个租户投影器")

    # 在实际应用中，这些投影器会在后台运行
    # tasks = [asyncio.create_task(p.run_forever()) for p in projectors]

    await engine.dispose()


async def performance_tuning_example():
    """性能调优示例"""
    print("\n🚀 6. 性能调优指南")

    performance_scenarios = {
        "高吞吐量批处理": {
            "config": OutboxProjectorConfig(
                batch_size=2000,           # 大批量
                sleep_busy=0.01,          # 极快轮询
                max_concurrent_projectors=8, # 高并发
                max_retry_attempts=20      # 更多重试
            ),
            "适用": "夜间批处理、数据同步"
        },
        "低延迟实时处理": {
            "config": OutboxProjectorConfig(
                batch_size=10,            # 小批量
                sleep_busy=0.001,         # 毫秒级轮询
                max_concurrent_projectors=15, # 极高并发
                max_retry_attempts=3       # 快速失败
            ),
            "适用": "实时通知、即时消息"
        },
        "资源节约模式": {
            "config": OutboxProjectorConfig(
                batch_size=100,           # 中等批量
                sleep_busy=1.0,           # 慢轮询
                sleep_idle_max=60.0,      # 长期空闲
                max_concurrent_projectors=2 # 低并发
            ),
            "适用": "资源受限环境、成本优化"
        }
    }

    for scenario_name, info in performance_scenarios.items():
        config = info["config"]
        print(f"   • {scenario_name}:")
        print(f"     配置: 批量={config.batch_size}, 轮询={config.sleep_busy}s")
        print(f"     适用: {info['适用']}")


async def main():
    """主演示函数"""
    print("🎯 OutboxProjector 配置外部化使用指南")
    print("=" * 50)

    try:
        await basic_usage_example()
        await custom_config_example()
        await template_config_example()
        await environment_config_example()
        await multi_tenant_example()
        await performance_tuning_example()

        print("\n💡 使用建议:")
        print("   1. 开发环境使用默认配置或 development 模板")
        print("   2. 生产环境通过环境变量设置关键参数")
        print("   3. 不同业务场景使用对应的性能调优模板")
        print("   4. 多租户场景为每个租户定制配置")
        print("   5. 使用配置验证确保参数合理性")

        print("\n🎉 OutboxProjector 配置外部化演示完成！")

    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
