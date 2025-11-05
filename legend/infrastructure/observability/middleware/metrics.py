"""
FastAPI 指标中间件
用于记录 HTTP 请求指标
"""
import logging
import time
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core import (
    LABEL_METHOD,
    LABEL_PATH,
    LABEL_STATUS,
    METRIC_HTTP_REQUEST_DURATION,
    METRIC_HTTP_REQUEST_SIZE,
    METRIC_HTTP_REQUESTS_TOTAL,
    METRIC_HTTP_RESPONSE_SIZE,
    IMetricsRecorder,
)

logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """指标中间件，用于记录 HTTP 请求指标"""
    
    def __init__(
        self, 
        app: FastAPI, 
        recorder: IMetricsRecorder,
        exclude_paths: Optional[list[str]] = None
    ):
        """初始化中间件
        
        Args:
            app: FastAPI 应用
            recorder: 指标记录器
            exclude_paths: 排除的路径列表
        """
        super().__init__(app)
        self.recorder = recorder
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """处理请求
        
        Args:
            request: HTTP 请求
            call_next: 下一个处理器
            
        Returns:
            Response: HTTP 响应
        """
        # 提取请求路径和方法
        path = request.url.path
        
        # 排除不需要记录的路径
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # 规范化路径，将ID等参数替换为占位符
        normalized_path = self._normalize_path(request)
        method = request.method
        
        # 记录请求大小
        request_size = 0
        if hasattr(request, "headers"):
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit():
                request_size = int(content_length)
        
        # 开始计时
        start_time = time.time()
        
        try:
            # 执行请求
            response = await call_next(request)
            
            # 计算请求时间
            duration = time.time() - start_time
            
            # 记录响应状态码
            status_code = response.status_code
            
            # 记录响应大小
            response_size = 0
            if hasattr(response, "headers"):
                content_length = response.headers.get("content-length")
                if content_length and content_length.isdigit():
                    response_size = int(content_length)
            
            # 异步记录指标
            await self._record_metrics(
                method, 
                normalized_path, 
                status_code, 
                duration, 
                request_size,
                response_size
            )
            
            return response
        except Exception as e:
            # 计算请求时间
            duration = time.time() - start_time
            
            # 异步记录错误指标
            await self._record_metrics(
                method, 
                normalized_path, 
                500, 
                duration, 
                request_size,
                0
            )
            
            # 记录错误日志
            logger.exception(f"Error processing request: {e}")
            
            # 重新抛出异常，让 FastAPI 处理
            raise
    
    def _normalize_path(self, request: Request) -> str:
        """规范化路径，将ID等参数替换为占位符
        
        Args:
            request: HTTP 请求
            
        Returns:
            str: 规范化后的路径
        """
        path = request.url.path
        
        # 提取路由模式，如果可用
        scope = request.scope
        if "route" in scope and hasattr(scope["route"], "path_format"):
            # 使用 FastAPI 的路由定义替换路径参数
            return scope["route"].path_format
        
        # 应用简单的启发式算法：
        # 将数字路径片段替换为 :id
        path_parts = path.strip("/").split("/")
        normalized_parts = []
        
        for part in path_parts:
            if part.isdigit() or (
                len(part) >= 24 and all(c.isalnum() or c == "-" for c in part)
            ):
                normalized_parts.append(":id")
            elif part.startswith("v") and part[1:].isdigit():
                # 匹配 v1, v2 等版本号
                normalized_parts.append(part)
            else:
                normalized_parts.append(part)
        
        # 重建路径
        normalized_path = "/" + "/".join(normalized_parts)
        return normalized_path
    
    async def _record_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        request_size: int,
        response_size: int
    ) -> None:
        """记录请求指标
        
        Args:
            method: HTTP 方法
            path: 规范化路径
            status_code: 状态码
            duration: 请求持续时间(秒)
            request_size: 请求大小(字节)
            response_size: 响应大小(字节)
        """
        labels = {
            LABEL_METHOD: method,
            LABEL_PATH: path
        }
        
        status_labels = {
            LABEL_METHOD: method,
            LABEL_PATH: path,
            LABEL_STATUS: str(status_code)
        }
        
        try:
            # 记录请求计数
            await self.recorder.increment_counter(
                METRIC_HTTP_REQUESTS_TOTAL,
                1.0,
                status_labels
            )
            
            # 记录请求持续时间
            await self.recorder.observe_histogram(
                METRIC_HTTP_REQUEST_DURATION,
                duration,
                labels
            )
            
            # 记录请求大小
            if request_size > 0:
                await self.recorder.observe_histogram(
                    METRIC_HTTP_REQUEST_SIZE,
                    float(request_size),
                    labels
                )
            
            # 记录响应大小
            if response_size > 0:
                await self.recorder.observe_histogram(
                    METRIC_HTTP_RESPONSE_SIZE,
                    float(response_size),
                    labels
                )
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    @staticmethod
    def setup(
        app: FastAPI, 
        recorder: IMetricsRecorder,
        exclude_paths: Optional[list[str]] = None
    ) -> None:
        """便捷设置方法
        
        Args:
            app: FastAPI 应用
            recorder: 指标记录器
            exclude_paths: 排除的路径列表
        """
        app.add_middleware(
            MetricsMiddleware, 
            recorder=recorder,
            exclude_paths=exclude_paths
        )