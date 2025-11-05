"""
指标记录器工厂使用示例
"""
import asyncio
import logging
import random
from typing import Any, Dict

from idp.framework.infrastructure.observability.core import (
    MetricMetadata,
    MetricType,
    ObservabilityConfig,
    StandardMetrics,
)
from idp.framework.infrastructure.observability.metrics.factory import (
    MetricsRecorderFactory,
    MetricsRecorderType,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def simulate_application_metrics(recorder_type: str = "MEMORY"):
    """模拟应用程序指标记录
    
    Args:
        recorder_type: 记录器类型，可选 "MEMORY" 或 "PROMETHEUS"
    """
    logger.info(f"初始化 {recorder_type} 指标记录器...")
    
    # 创建配置
    config = ObservabilityConfig.from_env(service_name="metrics-factory-example")
    
    # 更新配置，使用指定的记录器类型
    config.metrics.recorder_type = recorder_type
    
    # 使用工厂创建记录器
    metrics_recorder = MetricsRecorderFactory.create_from_config(config.metrics)
    
    # 注册自定义指标
    custom_metric = MetricMetadata(
        name="custom_operation_count",
        type=MetricType.COUNTER,
        help="自定义操作计数器",
        label_names=["operation_type", "status"]
    )
    
    if hasattr(metrics_recorder, "_register_metric"):
        metrics_recorder._register_metric(custom_metric)
    
    # 启动定期刷新任务
    await metrics_recorder.start_periodic_flush(interval=5.0)
    
    try:
        logger.info("开始记录模拟指标...")
        
        # 模拟HTTP请求
        for i in range(20):
            # 随机HTTP状态码
            status_code = random.choice([200, 200, 200, 201, 400, 404, 500])
            
            # 记录请求计数
            await metrics_recorder.increment_counter(
                name=StandardMetrics.HTTP_REQUEST_TOTAL.name,
                value=1.0,
                labels={
                    "method": "GET",
                    "path": "/api/items",
                    "status": str(status_code)
                }
            )
            
            # 记录请求处理时间
            duration = random.uniform(0.01, 0.5)
            await metrics_recorder.observe_histogram(
                name=StandardMetrics.HTTP_REQUEST_DURATION.name,
                value=duration,
                labels={
                    "method": "GET",
                    "path": "/api/items"
                }
            )
            
            # 模拟数据库连接
            await metrics_recorder.set_gauge(
                name=StandardMetrics.DB_CONNECTIONS.name,
                value=random.randint(5, 20),
                labels={
                    "pool_name": "main",
                    "state": "active" if recorder_type == "MEMORY" else "1"  # 为Prometheus使用数字
                }
            )
            
            # 模拟数据库操作
            db_duration = random.uniform(0.001, 0.1)
            await metrics_recorder.observe_histogram(
                name=StandardMetrics.DB_OPERATION_DURATION.name,
                value=db_duration,
                labels={
                    "operation": "select",
                    "table": "items"
                }
            )
            
            # 模拟自定义业务指标
            await metrics_recorder.increment_counter(
                name="custom_operation_count",
                value=1.0,
                labels={
                    "operation_type": "process_item",
                    "status": "success" if random.random() > 0.1 else "failure"
                }
            )
            
            # 短暂暂停
            await asyncio.sleep(0.1)
        
        # 确保所有指标都刷新到后端
        await metrics_recorder.flush()
        logger.info("指标记录完成，已刷新到后端")
        
        # 如果是内存记录器，输出指标摘要
        if recorder_type == "MEMORY" and hasattr(metrics_recorder, "get_metrics_summary"):
            summary = metrics_recorder.get_metrics_summary()
            logger.info(f"内存记录器指标摘要: {summary}")
            
            # 获取特定指标的值
            http_success_requests = metrics_recorder.get_counter_value(
                name=StandardMetrics.HTTP_REQUEST_TOTAL.name,
                labels={
                    "method": "GET",
                    "path": "/api/items",
                    "status": "200"
                }
            )
            logger.info(f"HTTP 200 请求总数: {http_success_requests}")
            
            # 获取直方图值
            durations = metrics_recorder.get_histogram_values(
                name=StandardMetrics.HTTP_REQUEST_DURATION.name,
                labels={
                    "method": "GET",
                    "path": "/api/items"
                }
            )
            avg_duration = sum(durations) / len(durations) if durations else 0
            logger.info(f"HTTP请求平均处理时间: {avg_duration:.4f} 秒")
        
    except Exception as e:
        logger.error(f"记录指标时发生错误: {e}")
    finally:
        # 关闭定期刷新任务
        if hasattr(metrics_recorder, "_flush_task") and metrics_recorder._flush_task:
            metrics_recorder._flush_task.cancel()
            try:
                await metrics_recorder._flush_task
            except asyncio.CancelledError:
                pass
        
        logger.info("指标记录示例完成")

async def compare_recorders():
    """比较不同类型的记录器"""
    logger.info("=== 开始比较不同类型的指标记录器 ===")
    
    # 先使用内存记录器
    logger.info("\n\n=== 使用内存记录器 ===")
    await simulate_application_metrics(recorder_type="MEMORY")
    
    # 再使用Prometheus记录器
    logger.info("\n\n=== 使用Prometheus记录器 ===")
    await simulate_application_metrics(recorder_type="PROMETHEUS")
    
    logger.info("=== 比较完成 ===")

if __name__ == "__main__":
    asyncio.run(compare_recorders()) 