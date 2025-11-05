"""
FastAPI 链路追踪中间件
用于追踪 HTTP 请求
"""
import logging
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core import (
    REQUEST_ID_HEADER_NAME,
    SPAN_HEADER_NAME,
    TRACE_HEADER_NAME,
    ITracer,
    SpanKind,
)

logger = logging.getLogger(__name__)

class TracingMiddleware(BaseHTTPMiddleware):
    """链路追踪中间件，用于追踪 HTTP 请求"""
    
    def __init__(
        self, 
        app: FastAPI, 
        tracer: ITracer,
        exclude_paths: Optional[list[str]] = None,
        request_id_header: str = REQUEST_ID_HEADER_NAME
    ):
        """初始化中间件
        
        Args:
            app: FastAPI 应用
            tracer: 追踪器
            exclude_paths: 排除的路径列表
            request_id_header: 请求ID的头部名称
        """
        super().__init__(app)
        self.tracer = tracer
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]
        self.request_id_header = request_id_header
    
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
        
        # 排除不需要追踪的路径
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # 提取请求ID或生成新的
        request_id = request.headers.get(self.request_id_header)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # 从请求头中提取追踪上下文
        self.tracer.extract_context(dict(request.headers))
        
        # 获取规范化路径
        normalized_path = self._normalize_path(request)
        
        # 开始一个新的根Span
        span_name = f"{request.method} {normalized_path}"
        
        # 设置基本的Span属性
        attributes = {
            "http.method": request.method,
            "http.url": str(request.url),
            "http.path": normalized_path,
            "request.id": request_id,
            "http.client_ip": request.client.host if hasattr(request, "client") and request.client else "",
            "http.user_agent": request.headers.get("user-agent", "")
        }
        
        # 提取并存储查询参数（注意脱敏）
        query_params = dict(request.query_params)
        if query_params:
            # 脱敏敏感信息
            self._sanitize_sensitive_data(query_params)
            attributes["http.query_string"] = str(query_params)
        
        # 启动一个服务端Span
        async with self.tracer.start_span(
            name=span_name,
            kind=SpanKind.SERVER,
            attributes=attributes
        ) as span:
            if not span:  # 可能因为采样率被跳过
                # 如果没有创建Span，仍然添加请求ID到响应中
                response = await call_next(request)
                response.headers[self.request_id_header] = request_id
                return response
            
            try:
                # 将追踪信息注入上下文
                request.state.trace_id = span.trace_id
                request.state.span_id = span.span_id
                request.state.request_id = request_id
                
                # 继续处理请求
                response = await call_next(request)
                
                # 记录响应状态码
                status_code = response.status_code
                span.set_attribute("http.status_code", status_code)
                
                # 添加响应头
                response.headers[self.request_id_header] = request_id
                response.headers[TRACE_HEADER_NAME] = span.trace_id
                response.headers[SPAN_HEADER_NAME] = span.span_id
                
                # 记录错误状态
                if status_code >= 400:
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", "http_error")
                    span.set_attribute("error.message", f"HTTP {status_code}")
                
                return response
            except Exception as e:
                # 记录异常
                span.record_exception(e)
                span.set_attribute("error", True)
                
                # 重新抛出异常
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
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> None:
        """脱敏敏感数据
        
        Args:
            data: 需要脱敏的数据
        """
        sensitive_keys = [
            "password", "token", "secret", "key", "auth", 
            "credential", "pwd", "passwd"
        ]
        
        for key in list(data.keys()):
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                data[key] = "***"
    
    @staticmethod
    def setup(
        app: FastAPI, 
        tracer: ITracer,
        exclude_paths: Optional[list[str]] = None,
        request_id_header: str = REQUEST_ID_HEADER_NAME
    ) -> None:
        """便捷设置方法
        
        Args:
            app: FastAPI 应用
            tracer: 追踪器
            exclude_paths: 排除的路径列表
            request_id_header: 请求ID的头部名称
        """
        app.add_middleware(
            TracingMiddleware, 
            tracer=tracer,
            exclude_paths=exclude_paths,
            request_id_header=request_id_header
        ) 