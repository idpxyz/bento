import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id  # 注入 request.state
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
