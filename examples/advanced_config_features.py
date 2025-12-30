"""高级配置功能示例 - 演示配置模板、验证、热更新等功能"""

import asyncio
import os
import sys
import tempfile
import json
from pathlib import Path

# 添加 Bento 到 Python 路径
sys.path.insert(0, '/workspace/bento/src')

from bento.config import (
    OutboxProjectorConfig,
    ConfigTemplates,
    create_config_from_template,
    validate_config,
    create_safe_config,
    ConfigValidator,
    ValidationRule,
)


async def demonstrate_config_templates():
    """演示配置模板功能"""
    print("🎨 配置模板功能演示\n")

    # 1. 列出所有可用模板
    templates = ConfigTemplates.list_templates()
    print("📋 可用配置模板:")
    for template in templates:
        description = ConfigTemplates.describe_template(template)
        print(f"   • {template}: {description}")
    print()

    # 2. 使用不同环境模板
    print("🌍 不同环境配置对比:")

    environments = ["development", "testing", "production"]
    for env in environments:
        config = ConfigTemplates.get_template(env)
        print(f"   {env.upper()}:")
        print(f"     批量大小: {config.batch_size}")
        print(f"     最大重试: {config.max_retry_attempts}")
        print(f"     忙时轮询: {config.sleep_busy}s")
        print(f"     租户ID: {config.default_tenant_id}")
        print()

    # 3. 使用场景优化模板
    print("🎯 场景优化配置:")

    scenarios = {
        "高吞吐量": "high_throughput",
        "低延迟": "low_latency",
        "资源节约": "resource_conservative",
        "批处理": "batch_processing"
    }

    for name, template_name in scenarios.items():
        config = ConfigTemplates.get_template(template_name)
        print(f"   {name}场景:")
        print(f"     批量: {config.batch_size}, 轮询: {config.sleep_busy}s")
        print(f"     重试: {config.max_retry_attempts}, 并发: {config.max_concurrent_projectors}")
        print()

    # 4. 自定义配置模板
    print("⚙️ 自定义配置 (基于生产环境模板):")
    custom_config = create_config_from_template(
        "production",
        {
            "batch_size": 2500,  # 更大批量
            "default_tenant_id": "my_service",
            "max_retry_attempts": 15,  # 更多重试
        }
    )
    print(f"   自定义批量: {custom_config.batch_size}")
    print(f"   自定义租户: {custom_config.default_tenant_id}")
    print(f"   自定义重试: {custom_config.max_retry_attempts}")
    print()


async def demonstrate_config_validation():
    """演示配置验证功能"""
    print("🔍 配置验证功能演示\n")

    # 1. 正常配置验证
    print("✅ 正常配置验证:")
    good_config = ConfigTemplates.production()
    result = validate_config(good_config)
    print(f"   验证结果: {result.get_summary()}")
    print()

    # 2. 错误配置验证
    print("❌ 错误配置验证:")
    try:
        bad_config = OutboxProjectorConfig(
            batch_size=-10,  # 无效值
            max_retry_attempts=1000,  # 过大值
            sleep_busy=100.0,  # 不合理值
            status_new="",  # 空字符串
        )
        result = validate_config(bad_config, strict=True)
        print(f"   验证结果: {result.get_detailed_report()}")
    except Exception as e:
        print(f"   配置创建失败: {e}")
    print()

    # 3. 警告配置验证
    print("⚠️ 有警告的配置:")
    warning_config = OutboxProjectorConfig(
        batch_size=10,  # 太小
        max_concurrent_projectors=20,  # 高并发
        sleep_busy=0.001,  # 极快轮询
        max_retry_attempts=50,  # 很多重试
    )
    result = validate_config(warning_config)
    print(result.get_detailed_report())
    print()

    # 4. 自定义验证规则
    print("🎛️ 自定义验证规则:")
    custom_rules = [
        ValidationRule(
            field_name="batch_size",
            min_value=100,  # 更严格的最小值
            error_message="批量大小不能小于100（企业环境要求）"
        ),
        ValidationRule(
            field_name="default_tenant_id",
            custom_validator=lambda x: x.startswith("prod_"),
            error_message="生产环境租户ID必须以 'prod_' 开头"
        ),
    ]

    validator = ConfigValidator(custom_rules)
    test_config = OutboxProjectorConfig(
        batch_size=50,  # 违反自定义规则
        default_tenant_id="test_tenant"  # 违反自定义规则
    )

    result = validator.validate(test_config)
    print(result.get_detailed_report())
    print()

    # 5. 安全配置创建
    print("🛡️ 安全配置创建:")
    try:
        safe_config = create_safe_config(
            batch_size=500,
            max_retry_attempts=8,
            default_tenant_id="safe_service"
        )
        print(f"   ✅ 安全配置创建成功: batch_size={safe_config.batch_size}")
    except ValueError as e:
        print(f"   ❌ 安全配置创建失败: {e}")
    print()


async def demonstrate_performance_scenarios():
    """演示不同性能场景的配置选择"""
    print("🚀 性能场景配置指南\n")

    scenarios = [
        {
            "name": "🏢 企业级生产环境",
            "template": "production",
            "description": "高可靠性，大批量处理，完善的重试机制"
        },
        {
            "name": "⚡ 实时通知系统",
            "template": "low_latency",
            "description": "毫秒级响应，小批量快速处理"
        },
        {
            "name": "📊 大数据ETL作业",
            "template": "batch_processing",
            "description": "超大批量，高容错，后台处理"
        },
        {
            "name": "💰 成本优化环境",
            "template": "resource_conservative",
            "description": "低资源消耗，长轮询间隔"
        },
        {
            "name": "🔬 开发调试环境",
            "template": "development",
            "description": "快速失败，调试友好，小批量"
        }
    ]

    for scenario in scenarios:
        config = ConfigTemplates.get_template(scenario["template"])

        print(f"{scenario['name']}:")
        print(f"   📝 {scenario['description']}")
        print(f"   ⚙️  配置参数:")
        print(f"      批量大小: {config.batch_size}")
        print(f"      并发数: {config.max_concurrent_projectors}")
        print(f"      轮询间隔: {config.sleep_busy}s (忙) / {config.sleep_idle}s (闲)")
        print(f"      重试策略: {config.max_retry_attempts}次, {config.backoff_multiplier}倍退避")

        # 计算一些关键指标
        max_delay = config.calculate_backoff_delay(config.max_retry_attempts)
        throughput_estimate = config.batch_size / (config.sleep_busy + 0.01)  # 估算吞吐量

        print(f"   📊 性能指标:")
        print(f"      估算吞吐量: ~{throughput_estimate:.0f} events/sec")
        print(f"      最大重试延迟: {max_delay}秒")
        print()


async def demonstrate_config_best_practices():
    """演示配置最佳实践"""
    print("💡 配置最佳实践建议\n")

    practices = [
        {
            "title": "🌍 环境配置策略",
            "tips": [
                "开发环境: 小批量 (20-50), 快速失败 (3次重试)",
                "测试环境: 中批量 (50-200), 标准重试 (5次)",
                "生产环境: 大批量 (500-2000), 充分重试 (10次+)",
                "使用环境变量覆盖关键参数"
            ]
        },
        {
            "title": "⚡ 性能优化原则",
            "tips": [
                "高吞吐量: 增加batch_size, 减少sleep_busy",
                "低延迟: 减少batch_size, 设置极小sleep_busy",
                "稳定性优先: 增加重试次数和退避时间",
                "资源节约: 增加轮询间隔，减少并发数"
            ]
        },
        {
            "title": "🛡️ 安全配置建议",
            "tips": [
                "总是验证配置参数合理性",
                "避免极端值 (如batch_size > 5000)",
                "监控配置变更的性能影响",
                "为生产环境预设合理的默认值"
            ]
        },
        {
            "title": "🔧 运维友好做法",
            "tips": [
                "使用有意义的租户ID标识服务",
                "配置关键参数为环境变量",
                "提供配置变更的回滚机制",
                "记录配置变更的审计日志"
            ]
        }
    ]

    for practice in practices:
        print(f"{practice['title']}:")
        for tip in practice['tips']:
            print(f"   • {tip}")
        print()


async def main():
    """主演示函数"""
    print("🎯 Bento Outbox 高级配置功能完整演示")
    print("=" * 50)
    print()

    try:
        await demonstrate_config_templates()
        await demonstrate_config_validation()
        await demonstrate_performance_scenarios()
        await demonstrate_config_best_practices()

        print("🎉 所有高级配置功能演示完成！")
        print("\n💡 接下来可以:")
        print("   1. 选择适合你场景的配置模板")
        print("   2. 使用验证功能确保配置安全")
        print("   3. 根据性能需求调整参数")
        print("   4. 在生产环境启用配置热更新")

    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
