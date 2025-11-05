"""
请求ID中间件
用于生成和传递请求ID
"""
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core import REQUEST_ID_HEADER_NAME


class RequestIdMiddleware(BaseHTTPMiddleware):
    """请求ID中间件，用于生成和传递请求ID"""
    
    def __init__(
        self, 
        app: FastAPI, 
        header_name: str = REQUEST_ID_HEADER_NAME,
        generator: Optional[Callable[[], str]] = None
    ):
        """初始化中间件
        
        Args:
            app: FastAPI 应用
            header_name: 请求ID的头部名称
            generator: 请求ID生成器函数
        """
        super().__init__(app)
        self.header_name = header_name
        self.generator = generator or self._default_generator
    
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
        # 尝试从请求头中获取请求ID
        request_id = request.headers.get(self.header_name)
        
        # 如果不存在，则生成新的
        if not request_id:
            request_id = self.generator()
        
        # 将请求ID添加到请求状态中
        request.state.request_id = request_id
        
        # 处理请求
        response = await call_next(request)
        
        # 在响应头中添加请求ID
        response.headers[self.header_name] = request_id
        
        return response
    
    @staticmethod
    def _default_generator() -> str:
        """默认的请求ID生成器
        
        Returns:
            str: 生成的请求ID
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def setup(
        app: FastAPI, 
        header_name: str = REQUEST_ID_HEADER_NAME,
        generator: Optional[Callable[[], str]] = None
    ) -> None:
        """便捷设置方法
        
        Args:
            app: FastAPI 应用
            header_name: 请求ID的头部名称
            generator: 请求ID生成器函数
        """
        app.add_middleware(
            RequestIdMiddleware, 
            header_name=header_name,
            generator=generator
        ) 