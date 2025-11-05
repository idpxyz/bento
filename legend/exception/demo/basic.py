from typing import Annotated

import sentry_sdk
from fastapi import FastAPI, Query

from idp.framework.exception.classified import DomainException, InfrastructureException
from idp.framework.exception.code.user import UserErrorCode
from idp.framework.exception.demo.request_context import TraceIDMiddleware
from idp.framework.exception.handler import register_exception_handlers
from idp.framework.exception.swagger import common_error_response

app = FastAPI()

sentry_sdk.init(
    dsn="https://a717fb1c8639f35bc78f4b60340ccc88@o4507072299991040.ingest.us.sentry.io/4507072302678016",  # 替换为你自己的 DSN
    traces_sample_rate=1.0,  # 或设置为 0.1 等
    environment="dev",
    send_default_pii=True,
)


app.add_middleware(TraceIDMiddleware)
register_exception_handlers(app)

@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0

@app.get(
    "/users/exists",
    summary="检查用户是否存在",
    description="根据邮箱地址判断用户是否存在",
    responses=common_error_response
)
async def check_user_exists(
    email: Annotated[str, Query(..., description="用户邮箱")]
):
    if email == "demo@example.com":
        raise DomainException(code=UserErrorCode.USER_ALREADY_EXISTS, details={"email": email}, cause=ValueError("用户已存在"))
    return {"email": email, "exists": False}

@app.get("/test-cause")
async def test_cause():
    try:
        raise ValueError("底层数据库连接失败")
    except Exception as e:
        raise DomainException(code=UserErrorCode.USER_ALREADY_EXISTS, details={"email": "test@x.com"}, cause=e)
       
@app.get("/test-hierarchy")
async def test_exception_hierarchy():
    """演示异常层次结构"""
    # 模拟不同层次的异常
    try:
        # 模拟基础设施层异常
        try:
            raise ConnectionError("数据库连接失败")
        except Exception as infra_error:
            # 模拟应用服务层封装异常
            service_error = InfrastructureException(
                code=UserErrorCode.SERVICE_UNAVAILABLE, 
                details={"service": "user_service"},
                cause=infra_error
            )
            raise service_error
    except DomainException as domain_error:
        # API层捕获并处理异常
        raise domain_error

@app.get("/error-analysis")
async def error_analysis():
    """提供更详细的错误分析示例"""
    try:
        try:
            # 模拟一个深层次的错误
            division_by_zero = 1 / 0
        except ZeroDivisionError as math_error:
            # 包装成数据库错误
            db_error = ValueError("数据库计算失败")
            db_error.__cause__ = math_error
            raise db_error
    except Exception as e:
        # 包装成领域异常
        domain_exc = DomainException(
            code=UserErrorCode.OPERATION_FAILED, 
            details={"operation": "calculate_stats"},
            cause=e
        )
        
        # 返回完整的错误链分析
        error_chain = []
        current = domain_exc
        while current:
            # 只使用通用的异常信息
            error_chain.append({
                "type": type(current).__name__,
                "message": str(current)
            })
            current = getattr(current, "cause", None) or getattr(current, "__cause__", None)
        
        # 安全地返回异常信息
        return {
            "exception_type": type(domain_exc).__name__,
            "exception_message": str(domain_exc),
            "error_chain": error_chain,
            "error_chain_length": len(error_chain),
            # 使用dir()列出所有可用属性，帮助调试
            "available_attributes": dir(domain_exc)
        }

@app.get("/debug-exception")
async def debug_exception():
    """调试DomainException类结构"""
    domain_exc = DomainException(
        code=UserErrorCode.USER_ALREADY_EXISTS,
        details={"email": "debug@example.com"},
        cause=ValueError("调试异常")
    )
    
    return {
        "exception_type": type(domain_exc).__name__,
        "exception_str": str(domain_exc),
        "exception_repr": repr(domain_exc),
        "exception_dict": {
            attr: getattr(domain_exc, attr)
            for attr in dir(domain_exc)
            if not attr.startswith('_') and not callable(getattr(domain_exc, attr))
        }
    }

if __name__ == "__main__":
    import uvicorn

    # 使用 uvicorn 运行 FastAPI 应用, 并启用自动重载

    
    uvicorn.run(
        "idp.framework.exception.demo.basic:app",
        host="0.0.0.0", 
        port=8000, 
        reload=True
        )
    