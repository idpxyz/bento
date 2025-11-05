"""
运行可观测性示例应用
"""
import logging
import os
import sys
from pathlib import Path

import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

def run_example_app():
    """运行示例应用"""
    # 确保当前工作目录正确
    workspace_dir = Path(__file__).resolve().parents[5]  # 获取到 /workspace 目录
    logger.info(f"设置工作目录: {workspace_dir}")
    os.chdir(workspace_dir)
    
    # 确保项目根目录在Python路径中
    if str(workspace_dir) not in sys.path:
        sys.path.insert(0, str(workspace_dir))
        logger.info(f"添加 {workspace_dir} 到 Python 路径")
    
    logger.info("=== 启动可观测性示例应用 ===")
    logger.info("应用将在 http://localhost:8000 上运行")
    logger.info("Prometheus 指标将在 http://localhost:9090/metrics 上可用")
    logger.info("内存指标可通过 http://localhost:8000/metrics/memory 查看")
    logger.info("指标比较示例：http://localhost:8000/metrics/comparison")
    logger.info("==========================================")
    
    try:
        # 启动 FastAPI 应用
        uvicorn.run(
            "infrastructure.observability.examples.example:app",
            host="0.0.0.0",
            port=8000,
            reload=False
        )
    except Exception as e:
        logger.error(f"启动应用失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        run_example_app()
    except KeyboardInterrupt:
        logger.info("应用被用户中断")
    except Exception as e:
        logger.exception(f"运行示例应用时出错: {e}")
        sys.exit(1) 