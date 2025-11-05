# 自定义中间件，如请求ID注入、限流、异常追踪

import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

def register_middlewares(app: FastAPI):
    app.add_middleware(RequestIDMiddleware)

