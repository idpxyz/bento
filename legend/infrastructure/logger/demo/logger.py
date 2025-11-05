import asyncio
import logging
import time
import traceback
from pathlib import Path

# Configure Python standard library logging for basic output
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from idp.framework.infrastructure.logger.manager import logger_manager
from idp.framework.bootstrap.component.logger_setup import logger_setup


# 创建一个示例函数，用于生成各种类型的日志
async def log_examples(logger):
    """生成各种类型的日志示例"""
    # 基本日志级别示例
    logger.debug("This is a DEBUG message", component="examples", category="basic")
    logger.info("This is an INFO message", component="examples", category="basic")
    logger.warning("This is a WARNING message", component="examples", category="basic")
    logger.error("This is an ERROR message", component="examples", category="basic")
    logger.critical("This is a CRITICAL message", component="examples", category="basic")
    
    # 结构化日志示例
    logger.info(
        "User login successful",
        event_type="user_login",
        user_id="user123",
        ip_address="192.168.1.1",
        login_method="password",
        duration_ms=120
    )
    
    # 性能指标示例
    start_time = time.time()
    await asyncio.sleep(0.1)  # 模拟操作
    elapsed = (time.time() - start_time) * 1000
    logger.info(
        "Database query completed",
        operation="query_users",
        query_type="SELECT",
        rows_returned=42,
        duration_ms=elapsed,
        performance_category="database"
    )
    
    # 异常和错误示例
    try:
        # 故意制造一个异常
        result = 1 / 0
    except Exception as e:
        logger.error(
            "Exception occurred during calculation",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,  # 包含完整的栈跟踪
            component="examples",
            category="exceptions"
        )
    
    # 业务事件示例
    logger.info(
        "Order processed successfully",
        event_type="order_processed",
        order_id="ORD-12345",
        customer_id="CUST-6789",
        order_total=99.95,
        items_count=3,
        payment_method="credit_card",
        business_unit="sales"
    )
    
    # 安全相关日志示例
    logger.warning(
        "Failed login attempt",
        event_type="security_event",
        user_id="unknown",
        ip_address="203.0.113.42",
        attempt_count=5,
        security_category="authentication",
        severity="medium"
    )


# 创建一个异步主函数，包含所有异步操作
async def main():
    try:
        # 清除任何现有的处理器
        logger_manager._processors = []
        
        print("=== Logger Demo Application ===")
        
        # 调用日志设置函数
        await logger_setup()
        
        # # 获取环境和配置信息
        # app_namespace = "app"
        # env = config.get(app_namespace, "env", "dev")
        # app_name = config.get(app_namespace, "app.name", "IDP Platform")
        # log_level = config.get(app_namespace, "logging.level", "INFO")
        
        # # 列出已添加的处理器
        # active_processors = ", ".join(p.__class__.__name__ for p in logger_manager._processors)
        # print(f"Environment: {env}, Application: {app_name}, Log Level: {log_level}")
        # print(f"Active processors: {active_processors}")
        
        # 获取logger
        logger = logger_manager.get_logger(__name__)
        logger.info("Logger initialized successfully", 
                   component="setup", 
                   event_type="initialization")
        
        # 生成日志示例
        print("Generating sample logs...")
        await log_examples(logger)
        
        # 等待异步操作完成
        await asyncio.sleep(2)
        
        # 列出生成的日志文件
        log_files = find_log_files()
        
        # 停止日志处理器
        await logger_manager.stop()
        
        return log_files
        
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        traceback.print_exc()
        return []


def find_log_files():
    """查找和显示生成的日志文件"""
    log_files = []
    log_dir = Path("logs")
    
    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        return []
    
    for file_pattern in ["*.log*", "*.json*"]:
        for file in log_dir.glob(file_pattern):
            log_files.append(file)
    
    if not log_files:
        print(f"No log files found in {log_dir}")
        return []
    
    print(f"Found {len(log_files)} log files:")
    for log_file in sorted(log_files):
        try:
            file_size = log_file.stat().st_size
            size_display = f"{file_size} bytes"
            if file_size > 1024:
                size_display = f"{file_size/1024:.1f} KB"
            
            print(f"  - {log_file.name} ({size_display})")
        except Exception as e:
            print(f"  - {log_file.name} (Error: {e})")
    
    return log_files


def print_summary(log_files):
    """打印日志演示摘要"""
    print("=== Logger Demo Summary ===")
    
    if not log_files:
        print("No log files were generated. Please check the configuration and permissions.")
        return
    
    print(f"Successfully generated {len(log_files)} log files:")
    for log_file in sorted(log_files):
        print(f"  - {log_file}")


# 只使用一次asyncio.run()来运行整个异步流程
if __name__ == "__main__":
    try:
        print("=== Starting Logger Demo ===")
        log_files = asyncio.run(main())
        print_summary(log_files)
        print("=== Logger Demo Completed ===")
    except KeyboardInterrupt:
        print("Demo interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()