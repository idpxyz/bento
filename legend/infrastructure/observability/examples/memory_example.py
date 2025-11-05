"""
内存指标记录器使用示例
"""
import asyncio
import logging
import random
from typing import Any, Dict

from idp.framework.infrastructure.observability.core import MetricMetadata, MetricType
from idp.framework.infrastructure.observability.metrics import MemoryMetricsRecorder

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def simulate_http_requests(recorder: MemoryMetricsRecorder, count: int = 10):
    """模拟HTTP请求并记录指标"""
    for i in range(count):
        # 模拟HTTP请求处理时间
        duration = random.uniform(0.01, 0.5)
        status_code = random.choice([200, 200, 200, 201, 400, 404, 500])
        
        # 记录请求计数
        await recorder.increment_counter(
            name="http_requests_total",
            labels={"method": "GET", "path": "/api/v1/items", "status": str(status_code)}
        )
        
        # 记录请求处理时间
        await recorder.observe_histogram(
            name="http_request_duration_seconds",
            value=duration,
            labels={"method": "GET", "path": "/api/v1/items"}
        )
        
        # 模拟随机仪表盘值
        await recorder.set_gauge(
            name="active_connections",
            value=random.randint(1, 100)
        )
        
        await asyncio.sleep(0.1)  # 模拟请求间隔

async def main():
    """主函数"""
    # 创建内存指标记录器
    recorder = MemoryMetricsRecorder(
        prefix="app",
        default_labels={"service": "api", "environment": "dev"}
    )
    
    # 注册自定义指标
    custom_metric = MetricMetadata(
        name="business_transactions",
        type=MetricType.COUNTER,
        help="业务交易计数器",
        label_names=["transaction_type", "status"]
    )
    recorder._register_metric(custom_metric)
    
    # 启动定期刷新任务
    await recorder.start_periodic_flush(interval=5.0)
    
    try:
        # 模拟记录指标
        logger.info("开始模拟记录指标...")
        await simulate_http_requests(recorder, count=20)
        
        # 模拟业务指标
        for _ in range(10):
            await recorder.increment_counter(
                name="business_transactions",
                value=1.0,
                labels={"transaction_type": "payment", "status": "success"}
            )
            await asyncio.sleep(0.2)
        
        # 确保所有指标都被刷新
        await recorder.flush()
        
        # 输出指标摘要
        logger.info("指标记录完成，输出摘要...")
        summary = recorder.get_metrics_summary()
        logger.info(f"指标摘要: {summary}")
        
        # 获取并输出特定指标的值
        http_requests = recorder.get_counter_value(
            name="http_requests_total",
            labels={"method": "GET", "path": "/api/v1/items", "status": "200"}
        )
        logger.info(f"HTTP 200 请求总数: {http_requests}")
        
        # 获取直方图值并计算平均值
        durations = recorder.get_histogram_values(
            name="http_request_duration_seconds",
            labels={"method": "GET", "path": "/api/v1/items"}
        )
        avg_duration = sum(durations) / len(durations) if durations else 0
        logger.info(f"HTTP请求平均处理时间: {avg_duration:.4f}秒")
        
        # 清空指标数据
        recorder.clear()
        logger.info("已清空所有指标数据")
        
    except Exception as e:
        logger.error(f"发生错误: {e}")
    finally:
        # 在实际应用中，这通常在应用关闭时执行
        if hasattr(recorder, "_flush_task") and recorder._flush_task:
            recorder._flush_task.cancel()
            try:
                await recorder._flush_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    asyncio.run(main()) 